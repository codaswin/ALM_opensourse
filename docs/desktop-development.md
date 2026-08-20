# Desktop Development

## Prerequisites

- Python 3.12 and dependencies from backend/requirements.txt
- Node 20 and the frontend npm lockfile
- Stable Rust
- Tauri platform prerequisites, including WebKitGTK development packages on Linux

## Checks

Run the version check, backend tests and safety audits, frontend lint/build, sidecar build, then Cargo check. The native checks must run on Windows, macOS, and Linux rather than cross-compiling installers from one host.

The scripts/build-sidecar.sh script names the executable using Rust's host target tuple so Tauri can include it through externalBin.

Desktop mode is configured only by the native owner. For direct sidecar debugging, pass an absolute --app-data-dir and write a 32-character-or-longer launch token followed by a newline to stdin. Never place the token in argv, files, logs, or source configuration.
