# ADR 0003: Native secret storage and signed updates

- Status: Accepted for implementation
- Date: 2026-08-20

## Context

Desktop installations hold provider credentials and can execute externally visible LinkedIn actions. Storing secrets in JavaScript, SQLite, logs, command-line arguments, or plaintext Linux fallbacks is unacceptable. Updates can alter the same privileged execution path.

## Decision

Use a backend `CredentialStore` interface. Server mode retains encrypted database credentials. Desktop mode reads secrets from Windows Credential Manager, macOS Keychain, or an available Linux Secret Service through a maintained keyring adapter. If secure storage is unavailable, setup fails with a recoverable error; there is no plaintext fallback.

Only non-secret connection metadata is stored in SQLite. Saving a credential triggers a provider connectivity and permission test and records a structured state.

Desktop updates require signed artifacts and signed update metadata. Start with a stable channel and user-initiated update checks. Back up mutable data before any update that runs a schema or RAG-format migration.

## Consequences

- Linux release support is gated on verified keyring behavior.
- Tokens and credentials require explicit log-redaction tests.
- Signing identities, rotation, revocation, rollback, and incident procedures are release blockers, not post-release tasks.
