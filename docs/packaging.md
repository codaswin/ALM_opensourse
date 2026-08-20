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
