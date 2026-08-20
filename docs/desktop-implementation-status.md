# Desktop Implementation Status

## Implemented and locally verified

- Runtime profiles preserve hosted-server behavior and make desktop mode local-first.
- Desktop identity, per-launch loopback authentication, SQLite domain/runtime state, app-data paths, migrations, backup-before-migrate, and OS-keyring-only credential values are implemented.
- Legacy notification, episodic, and semantic-memory ownership gaps are migrated and user-scoped; working-memory keys and FAISS stores are isolated.
- RAG snapshots use cross-platform locking, versioned metadata, bounded generations, dimension checks, and metadata-driven rebuild.
- Tauri owns a frozen FastAPI sidecar on a dynamic loopback port, sends its launch token through stdin, supports single-instance focus, and stops the child on exit.
- The React/Vite UI handles desktop bootstrap, local-owner onboarding, capability-aware navigation, structured startup failures, and the safety pause/resume switch.
- Hosted login, CSRF, RBAC, PostgreSQL, Redis, encrypted database credentials, Docker/VPS deployment, and user administration remain available.
- The Linux PyInstaller sidecar starts from a clean application-data directory and completes migrations and shutdown without Python, PostgreSQL, or Redis services.

## Release prerequisites outside this workstation

- Native Tauri compilation on this Linux host needs the system WebKitGTK/GLib development packages. Installing them requires administrator access.
- Windows and macOS sidecars/installers must be built and smoke-tested on native runners; cross-compilation is not an acceptance substitute.
- Production artifacts still require platform signing/notarization identities, updater signing keys and endpoint, SBOM/license review, and clean-machine install/upgrade/rollback/uninstall drills.
- Native keyring behavior must be exercised in real Windows Credential Manager, macOS Keychain, and supported Linux Secret Service sessions.
- Active tag/push release automation is intentionally absent until the repository owner explicitly authorizes workflows that publish external releases.

Until those prerequisites are completed, version 0.1.0 is a validated desktop development build, not a signed production release.
