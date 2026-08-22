use rand::RngCore;
use serde::Serialize;
use shared_child::SharedChild;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use tauri::{Emitter, Manager, RunEvent, State};

#[cfg(windows)]
const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;

const SIDECAR_NAME: &str = "ai-linkedin-backend";

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConnection {
    origin: String,
    launch_token: String,
}

#[derive(Default)]
struct BackendState {
    connection: Mutex<Option<RuntimeConnection>>,
    child: Mutex<Option<Arc<SharedChild>>>,
}

/// Resolves the sidecar binary next to this app's own executable — the same
/// convention `tauri-plugin-shell`'s `sidecar()` resolver uses (and what
/// `externalBin`/`tauri build` actually places there). Replicated directly
/// here, rather than spawning through the plugin, because the plugin gives
/// us no way to put the child into its own process group at spawn time —
/// see `spawn_backend` and `kill_backend` for why that's required.
fn resolve_sidecar_path() -> Result<PathBuf, String> {
    let exe_path = tauri::utils::platform::current_exe()
        .map_err(|error| format!("Could not resolve current executable path: {error}"))?;
    let exe_dir = exe_path
        .parent()
        .ok_or_else(|| "Current executable has no parent directory".to_string())?;
    // `cargo test` puts the test binary in a "deps" subdirectory; the
    // sidecar itself sits one level up, alongside the real app binary.
    let base_dir = if exe_dir.ends_with("deps") {
        exe_dir.parent().unwrap_or(exe_dir)
    } else {
        exe_dir
    };
    #[cfg_attr(not(windows), allow(unused_mut))]
    let mut path = base_dir.join(SIDECAR_NAME);
    #[cfg(windows)]
    path.as_mut_os_string().push(".exe");
    Ok(path)
}

fn kill_backend(app: &tauri::AppHandle) {
    let Some(child) = app
        .state::<BackendState>()
        .child
        .lock()
        .ok()
        .and_then(|mut guard| guard.take())
    else {
        // Already killed (or never started) — nothing to do. The Mutex +
        // take() above make this function safe to call more than once
        // concurrently (raw SIGTERM/SIGINT racing a window-close, say):
        // only one caller ever observes `Some`.
        return;
    };

    // spawn_backend puts the backend into a brand-new process group that
    // this app creates and owns outright (process_group(0) on Unix, at
    // spawn time — never inherited from whatever launched us: a terminal,
    // a display-manager session, systemd). Because of that, the backend's
    // own PID *is* that group's ID, and signalling -pgid here is
    // guaranteed to reach only the backend and its own descendants —
    // never anything that existed before we spawned it. That guarantee is
    // what makes it safe to reach PyInstaller's onefile bootloader AND the
    // real interpreter process it forks (confirmed by launching a packaged
    // build and observing that killing only the tracked PID left that
    // forked interpreter running as an orphan indefinitely): both live in
    // the same group we created, so one signal reaches both.
    #[cfg(unix)]
    {
        let pgid = child.id() as libc::pid_t;
        unsafe {
            libc::kill(-pgid, libc::SIGTERM);
        }
    }
    // Second attempt: a direct kill of the tracked (bootloader) PID only —
    // never the group — as extra certainty in case the group signal above
    // didn't reach it (e.g. it had already detached). This is also the
    // only signal sent on Windows, where CREATE_NEW_PROCESS_GROUP at spawn
    // time (see spawn_backend) still isolates the backend from console
    // Ctrl+C/Ctrl+Break meant for this app, but a full descendant-tree
    // kill there would need a Job Object, which is out of scope here and
    // still needs its own validation on a native Windows runner.
    let _ = child.kill();
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

    let sidecar_path = resolve_sidecar_path()?;
    let mut command = Command::new(&sidecar_path);
    command
        .arg("--app-data-dir")
        .arg(&app_data_dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    // Explicitly create and own the backend's process group right here, at
    // spawn time — never inspect/assume one afterward (that's the bug this
    // replaces: the previous code read back whatever group the child
    // happened to inherit from this app's own group via getpgid(), which
    // on at least one real machine was shared with far more than this
    // app, so killing "-pgid" killed far more than the backend too).
    // `process_group(0)` runs setpgid(0, 0) in the child between fork and
    // exec — atomically, before the backend's own code ever runs — making
    // the child the leader of a fresh group whose ID equals its own PID.
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    // CREATE_NEW_PROCESS_GROUP isolates the backend from console
    // Ctrl+C/Ctrl+Break signals meant for this app; Windows has no
    // equivalent of a POSIX process group for kill_backend's group-signal
    // path above, so termination there still relies on the single-PID
    // kill below.
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NEW_PROCESS_GROUP);
    }

    let shared_child = SharedChild::spawn(&mut command)
        .map_err(|error| format!("Could not start backend sidecar: {error}"))?;

    let mut stdin = shared_child
        .take_stdin()
        .ok_or_else(|| "Backend sidecar has no stdin".to_string())?;
    stdin
        .write_all(format!("{launch_token}\n").as_bytes())
        .map_err(|error| format!("Could not authenticate backend sidecar: {error}"))?;
    drop(stdin);

    let stdout = shared_child
        .take_stdout()
        .ok_or_else(|| "Backend sidecar has no stdout".to_string())?;
    let stderr = shared_child
        .take_stderr()
        .ok_or_else(|| "Backend sidecar has no stderr".to_string())?;

    let shared_child = Arc::new(shared_child);
    app.state::<BackendState>()
        .child
        .lock()
        .map_err(|_| "Backend process state is unavailable".to_string())?
        .replace(shared_child.clone());

    // Stdout reader — watches for the one-line JSON "ready" event.
    {
        let app = app.clone();
        let launch_token = launch_token.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) {
                    if value.get("event").and_then(|item| item.as_str()) == Some("ready") {
                        if let Some(origin) = value.get("origin").and_then(|item| item.as_str()) {
                            let connection = RuntimeConnection {
                                origin: origin.to_string(),
                                launch_token: launch_token.clone(),
                            };
                            if let Ok(mut state) = app.state::<BackendState>().connection.lock() {
                                state.replace(connection.clone());
                            }
                            let _ = app.emit("backend-ready", connection);
                        }
                    }
                }
            }
        });
    }

    // Stderr reader — forwards each line as a diagnostic event.
    {
        let app = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                let _ = app.emit("backend-error", line);
            }
        });
    }

    // Wait thread — the single place that detects the process exiting
    // (whether on its own or via kill_backend), reaps it, and emits
    // backend-stopped exactly once. This runs regardless of who/what
    // caused the exit, so it also covers the "backend crashed on its own"
    // case that kill_backend never sees.
    {
        let app = app.clone();
        std::thread::spawn(move || {
            if let Ok(status) = shared_child.wait() {
                if let Ok(mut state) = app.state::<BackendState>().connection.lock() {
                    state.take();
                }
                let _ = app.emit("backend-stopped", status.code());
            }
        });
    }

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

#[cfg(all(test, unix))]
mod tests {
    use std::io::{BufRead, BufReader};
    use std::os::unix::process::CommandExt;
    use std::process::{Command, Stdio};
    use std::time::{Duration, Instant};

    fn process_exists(pid: libc::pid_t) -> bool {
        unsafe { libc::kill(pid, 0) == 0 }
    }

    fn wait_until<F: Fn() -> bool>(timeout: Duration, condition: F) -> bool {
        let deadline = Instant::now() + timeout;
        loop {
            if condition() {
                return true;
            }
            if Instant::now() >= deadline {
                return false;
            }
            std::thread::sleep(Duration::from_millis(25));
        }
    }

    /// Exercises the exact invariant `kill_backend` relies on: a child
    /// spawned with `process_group(0)` becomes the leader of its own new
    /// group (distinct from ours), a signal to that group's negative PID
    /// reaches a process the child itself forks (standing in for
    /// PyInstaller's bootloader forking the real interpreter) — and,
    /// critically, never reaches a sibling process left in this test's own
    /// group. This is the property whose absence caused the group signal
    /// to escape further than intended in production.
    #[test]
    fn process_group_signal_reaches_forked_descendant_but_not_a_sibling() {
        let mut sentinel = Command::new("sleep")
            .arg("30")
            .spawn()
            .expect("failed to spawn sentinel");

        let mut child = Command::new("sh")
            .args(["-c", "sleep 30 & echo $!; wait"])
            .process_group(0)
            .stdout(Stdio::piped())
            .spawn()
            .expect("failed to spawn test child");

        let child_pid = child.id() as libc::pid_t;
        let child_pgid = unsafe { libc::getpgid(child_pid) };
        let our_pgid = unsafe { libc::getpgid(0) };
        assert_eq!(
            child_pgid, child_pid,
            "child must become the leader of its own new group"
        );
        assert_ne!(
            child_pgid, our_pgid,
            "child's group must not be this test process's own group"
        );

        let mut descendant_pid_line = String::new();
        BufReader::new(child.stdout.take().expect("piped stdout"))
            .read_line(&mut descendant_pid_line)
            .expect("failed to read forked descendant's pid");
        let descendant_pid: libc::pid_t = descendant_pid_line
            .trim()
            .parse()
            .expect("child did not print a pid");

        assert!(
            wait_until(Duration::from_secs(1), || process_exists(descendant_pid)),
            "forked descendant should be running before the kill"
        );

        unsafe {
            libc::kill(-child_pgid, libc::SIGTERM);
        }
        let _ = child.wait();

        assert!(
            wait_until(Duration::from_secs(2), || !process_exists(descendant_pid)),
            "forked descendant survived the group signal — this is the orphan bug"
        );
        assert!(
            process_exists(sentinel.id() as libc::pid_t),
            "a process outside the backend's group must never be touched"
        );

        let _ = sentinel.kill();
        let _ = sentinel.wait();
    }
}
