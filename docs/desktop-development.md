# Desktop Development

## Prerequisites

- Python 3.12 and dependencies from backend/requirements.txt
- Node 20 and the frontend npm lockfile
- Stable Rust
- Tauri platform prerequisites, including WebKitGTK development packages on Linux

### Per-OS native prerequisites

Tauri requires the OS's own native webview toolkit; there is no cross-compiled substitute for any of these.

- **Linux**: `libwebkit2gtk-4.1-dev`, `libjavascriptcoregtk-4.1-dev`, `libgtk-3-dev`, `libsoup-3.0-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, and `build-essential` (Debian/Ubuntu package names; see the [Tauri Linux prerequisites](https://v2.tauri.app/start/prerequisites/) for other distributions). Installing these requires administrator access on the host — `.github/workflows/ci.yml`'s `desktop` job installs them automatically on the ephemeral `ubuntu-latest` runner via `apt-get`.
- **Windows**: Visual Studio Build Tools (the "Desktop development with C++" workload) and the WebView2 runtime (preinstalled on Windows 11 and recent Windows 10; Tauri's bundler can also embed it). No extra packages are needed on `windows-latest` GitHub-hosted runners.
- **macOS**: Xcode Command Line Tools (`xcode-select --install`). No extra packages are needed on `macos-latest` GitHub-hosted runners.

## Checks

Run the version check, backend tests and safety audits, frontend lint/build, sidecar build, then Cargo check. The native checks must run on Windows, macOS, and Linux rather than cross-compiling installers from one host — for compile validation, `.github/workflows/ci.yml`'s `desktop` job now does exactly that on every push/PR, natively, on all three OSes (`docs/packaging.md`). That job stops at `cargo check`; it does not run `tauri build` or produce installers, so a local run of the full sequence below is still required before a release.

```bash
python scripts/check-version.py
pytest backend/tests backend/evals --cov=backend/app --cov=backend/evals --cov-fail-under=80
python -m backend.app.safety.audit
cd frontend && npm run lint && npm run build && cd ..
bash scripts/build-sidecar.sh
cd src-tauri && cargo check && cd ..
```

To produce an actual installer once native prerequisites are installed: `cd src-tauri && cargo tauri build` (or `npx @tauri-apps/cli build` from the repository root) — this drives `beforeBuildCommand`/`frontendDist` from `tauri.conf.json` and bundles the sidecar named in `externalBin`.

The scripts/build-sidecar.sh script names the executable using Rust's host target tuple so Tauri can include it through externalBin. It resolves `pyinstaller` from `PATH` first (so a plain `pip install pyinstaller` works in CI or any shell) and falls back to this repository's own `.venv` (Unix or Windows layout) for local development.

Desktop mode is configured only by the native owner. For direct sidecar debugging, pass an absolute --app-data-dir and write a 32-character-or-longer launch token followed by a newline to stdin. Never place the token in argv, files, logs, or source configuration.
