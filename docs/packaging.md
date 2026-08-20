# Desktop Packaging

Packaging runs natively on each target OS. PyInstaller bundles FastAPI, Alembic migrations, FAISS, provider SDKs, SQLite, keyring, and application modules. Tauri bundles that target-specific executable with the optimized React output.

Required native smoke checks:

1. Install on a clean machine without Python, PostgreSQL, or Redis.
2. Launch and reach authenticated readiness.
3. Verify SQLite migration, RAG write/read, native keyring, approval gating, and provider-client imports.
4. Close and confirm the sidecar exits.
5. Upgrade while preserving data and creating a migration backup.
6. Uninstall while preserving user data by default.

Generated sidecars, Cargo target files, and PyInstaller build/dist files are release artifacts and are excluded from Git.

## Linux: done on this workstation

`cargo tauri build` was run for real here (after installing `libwebkit2gtk-4.1-dev`, `libjavascriptcoregtk-4.1-dev`, `libgtk-3-dev`, `libsoup-3.0-dev`, `libayatana-appindicator3-dev`, `librsvg2-dev`, `build-essential`) and produced a working `.deb`, `.rpm`, and `.AppImage`. Checks 1, 2, and 4 above passed against the `.AppImage`: it launched with no manually-started Python/PostgreSQL/Redis process, reached `GET /health` → 200 and correctly rejected `GET /runtime/bootstrap` without the launch token (401), migrated a fresh SQLite database, and closing it left zero orphan processes and unmounted its FUSE mount cleanly. Check 3 is only partially done — provider-client imports are confirmed (the frozen binary would fail to start otherwise) but RAG write/read, native keyring, and approval gating were not exercised through the UI. Checks 5 and 6 (upgrade, uninstall via the actual `.deb`/`.rpm`, not just the portable AppImage) are not done. See `docs/desktop-implementation-status.md` for the two real bugs this run found and fixed (a `beforeBuildCommand` working-directory bug, and a sidecar orphan-process bug).

## CI compile validation

`.github/workflows/ci.yml`'s `desktop` job runs `scripts/build-sidecar.sh` and `cargo check` natively on `ubuntu-latest`, `windows-latest`, and `macos-latest` for every push/PR — the Linux WebKitGTK/GLib development headers are installed by that job on the ephemeral runner via `apt-get`, which has passwordless sudo there. This validates that the shell compiles on every target OS; it does not run `tauri build`, sign anything, or produce installers on Windows/macOS, so it is not a substitute for the native clean-machine install/upgrade/uninstall smoke tests above on those two platforms.

Native icons live in `src-tauri/icons/` (source: `app-icon.svg`) and are referenced by `bundle.icon` in `src-tauri/tauri.conf.json`.
