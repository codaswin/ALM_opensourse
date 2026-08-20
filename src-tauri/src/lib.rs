use rand::RngCore;
use serde::Serialize;
use std::sync::Mutex;
use tauri::{Emitter, Manager, RunEvent, State};
use tauri_plugin_shell::{process::CommandChild, process::CommandEvent, ShellExt};

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConnection {
    origin: String,
    launch_token: String,
}

#[derive(Default)]
struct BackendState {
    connection: Mutex<Option<RuntimeConnection>>,
    child: Mutex<Option<CommandChild>>,
}

fn kill_backend(app: &tauri::AppHandle) {
    if let Ok(mut child) = app.state::<BackendState>().child.lock() {
        if let Some(process) = child.take() {
            // The frozen sidecar's PyInstaller onefile bootloader forks a
            // second process (the real interpreter) that inherits the
            // bootloader's process group instead of getting its own —
            // confirmed by launching a packaged build and observing that
            // killing only the tracked child PID left that grandchild
            // running as an orphan indefinitely. Signal the whole process
            // group first so the real worker is reached too, then fall
            // back to the plugin's own single-PID kill as a second attempt
            // in case the group signal didn't reach it (e.g. it already
            // detached). Windows has no equivalent of POSIX process groups
            // here; that path still relies on the single-PID kill below
            // and needs its own validation on a native Windows runner.
            #[cfg(unix)]
            {
                let pid = process.pid() as libc::pid_t;
                let pgid = unsafe { libc::getpgid(pid) };
                if pgid > 0 {
                    unsafe {
                        libc::kill(-pgid, libc::SIGTERM);
                    }
                }
            }
            let _ = process.kill();
        }
    }
}

#[tauri::command]
fn runtime_connection(state: State<'_, BackendState>) -> Result<RuntimeConnection, String> {
    state
        .connection
        .lock()
        .map_err(|_| "Backend state is unavailable".to_string())?
        .clone()
        .ok_or_else(|| "Backend is still starting".to_string())
}

fn spawn_backend(app: tauri::AppHandle) -> Result<(), String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Could not resolve application data directory: {error}"))?;
    std::fs::create_dir_all(&app_data_dir)
        .map_err(|error| format!("Could not create application data directory: {error}"))?;

    let mut token_bytes = [0_u8; 32];
    rand::rng().fill_bytes(&mut token_bytes);
    let launch_token = token_bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();

    let command = app
        .shell()
        .sidecar("ai-linkedin-backend")
        .map_err(|error| format!("Could not locate backend sidecar: {error}"))?
        .args(["--app-data-dir", &app_data_dir.to_string_lossy()]);
    let (mut events, mut child) = command
        .spawn()
        .map_err(|error| format!("Could not start backend sidecar: {error}"))?;
    child
        .write(format!("{launch_token}\n").as_bytes())
        .map_err(|error| format!("Could not authenticate backend sidecar: {error}"))?;
    app.state::<BackendState>()
        .child
        .lock()
        .map_err(|_| "Backend process state is unavailable".to_string())?
        .replace(child);

    tauri::async_runtime::spawn(async move {
        while let Some(event) = events.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) {
                        if value.get("event").and_then(|item| item.as_str()) == Some("ready") {
                            if let Some(origin) = value.get("origin").and_then(|item| item.as_str())
                            {
                                let connection = RuntimeConnection {
                                    origin: origin.to_string(),
                                    launch_token: launch_token.clone(),
                                };
                                if let Ok(mut state) = app.state::<BackendState>().connection.lock()
                                {
                                    state.replace(connection.clone());
                                }
                                let _ = app.emit("backend-ready", connection);
                            }
                        }
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let _ = app.emit("backend-error", String::from_utf8_lossy(&bytes).to_string());
                }
                CommandEvent::Terminated(payload) => {
                    if let Ok(mut state) = app.state::<BackendState>().connection.lock() {
                        state.take();
                    }
                    let _ = app.emit("backend-stopped", payload.code);
                }
                _ => {}
            }
        }
    });
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .manage(BackendState::default())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        // Registering this plugin unconditionally panics `.build()` at
        // startup ("invalid type: null, expected struct Config") unless
        // `tauri.conf.json` has a `plugins.updater` block with a real
        // pubkey/endpoint — confirmed by actually launching a packaged
        // build, not just `cargo check`. There is no real signing identity
        // yet (see docs/releasing.md); re-add this once the repository
        // owner supplies one and configures `plugins.updater`, rather than
        // shipping a placeholder key that could be mistaken for a real one.
        // .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![runtime_connection])
        .setup(|app| spawn_backend(app.handle().clone()).map_err(Into::into))
        .build(tauri::generate_context!())
        .expect("failed to build AI LinkedIn Manager");

    // `RunEvent::ExitRequested` below only fires for the graceful
    // window-close / `app.exit()` path. A raw SIGTERM/SIGINT (`kill`,
    // systemd stopping the unit, a session logout, many window managers'
    // "force quit") bypasses that event loop entirely — confirmed by
    // launching a packaged build and sending it SIGTERM directly, which
    // left the frozen Python sidecar running as an orphan. This handler
    // covers that path too, per desktopv.md #32 ("do not leave Python
    // servers running after the desktop application exits unintentionally").
    let signal_handle = app.handle().clone();
    ctrlc::set_handler(move || {
        kill_backend(&signal_handle);
        std::process::exit(0);
    })
    .expect("failed to register termination signal handler");

    app.run(|app, event| {
        if let RunEvent::ExitRequested { .. } = event {
            kill_backend(app);
        }
    });
}
