# Desktop Releasing

1. Update VERSION, the backend API version, frontend package version, Cargo package version, and Tauri version together. scripts/check-version.py enforces equality.
2. Run backend, frontend, migration, safety, native-shell, and packaged-sidecar checks on all supported targets.
3. Generate and review the dependency/SBOM and license inventory.
4. Configure platform code-signing/notarization identities and Tauri updater signing secrets.
5. Create signed draft artifacts for the version tag.
6. Install, upgrade, rollback, and uninstall the draft artifacts on clean target machines before publishing.

Never publish unsigned update metadata or artifacts. Keep releases as drafts when signing, notarization, platform keyring, or rollback verification is incomplete.

Active push/tag release automation is intentionally not installed without explicit repository-owner authorization because it can create external releases. The documented commands and local build scripts remain safe to run manually.
