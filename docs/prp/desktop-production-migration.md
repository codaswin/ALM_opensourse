# Product Requirements Plan: Production Desktop Migration

Status: Active  
Source brief: `desktopv.md`  
Audit: `docs/desktop-migration-audit.md`

## Outcome

Deliver installable, signed Windows, macOS, and Linux desktop applications that reuse the existing React UI and Python business core, require no user-managed Python/PostgreSQL/Redis services, and preserve hosted-server operation and all safety guarantees.

## Non-goals

- Rewriting agents or the frontend in Rust
- Forking business behavior between desktop and server
- Removing server multi-user authentication
- Silent background execution, auto-start, or data deletion
- Bypassing approvals because the desktop has one local owner
- Shipping unsigned production artifacts or plaintext credential fallback

## Required capabilities

### Shared core

- Five existing agents and custom harness remain functional.
- All LLM traffic continues through the model router.
- Tool schemas and approval flags remain centralized.
- Approval, retry, idempotency, kill-switch, guardrail, rate, and cost behavior remains identical across modes.

### Desktop runtime

- Tauri owns one frozen FastAPI sidecar.
- Dynamic loopback port and per-launch authentication.
- Explicit startup, migration, readiness, recovery, and shutdown states.
- One stable local owner without recurring login.
- SQLite domain and runtime state with backup/migration support.
- Installation/workspace-scoped RAG with cross-platform locking and rebuild.
- Native secure credential storage with connectivity/permission status.
- Initial scheduler behavior is run-while-open and clearly presented.

### Hosted runtime

- Preserve session/CSRF/RBAC authentication and user administration.
- Preserve PostgreSQL, Redis, encrypted credential rows, and distributed scheduling.
- Repair known ownership gaps and validate adversarial isolation.

### User experience

- First-run onboarding and connection verification.
- Structured error and remediation states with return routes.
- Backend lifecycle/health indication and diagnostics export.
- Safe update, backup, restore, reset, and uninstall behavior.
- Native notifications/tray/autostart only as explicit later capabilities.

## Implementation sequence

### Milestone 1: Contracts and characterization

- Accept ADRs for shell, runtime/storage, and credentials/updates.
- Introduce immutable runtime profile with server compatibility default.
- Document architecture, security, and data boundaries.
- Keep safety tests green and add runtime-profile tests.

Exit: documents reviewed; runtime contract typed/tested; no server behavior change.

### Milestone 2: Runtime adapters

- Define identity, state, credential, path, and scheduler-coordination protocols.
- Wrap existing server implementations without changing behavior.
- Implement SQLite state and desktop local-owner adapters.
- Remove import-time path/config assumptions.
- Add cross-engine, persistence, and isolation contract tests.

Exit: desktop core starts without Redis; server suite remains green.

### Milestone 3: Data hardening

- Add ownership migrations for legacy memory and notification records.
- Namespace runtime keys.
- Introduce cross-platform RAG lock, workspace layout, manifest, backup, and rebuild.
- Implement migration backup and structured recovery errors.

Exit: two simulated owners/installations cannot collide or read each other's data; forced interruption recovers safely.

### Milestone 4: Native spike

- Scaffold Tauri with minimal capabilities.
- Freeze and bundle the Python sidecar on native CI runners.
- Implement authenticated dynamic-port lifecycle and single-instance behavior.
- Test FAISS, cryptography, keyring, Composio, SQLite, and provider clients in packaged builds.

Exit: clean-machine install/start/quit on each target without prerequisites or orphan processes.

### Milestone 5: Desktop UX

- Add runtime bootstrap and capability-aware navigation.
- Skip login/user administration in desktop mode.
- Add onboarding, connection tests, diagnostics, recovery routes, error boundary, and lifecycle status.
- Add frontend unit/component/e2e coverage.

Exit: first-run, credential failure, offline provider, migration failure, restart, and approval journeys pass.

### Milestone 6: Release engineering and hardening

- Canonical version and release notes.
- Native icons/metadata/installers.
- Signing/notarization, SBOM/license inventory, signed updater, staged channel, and rollback.
- Backup/restore, kill-switch, update-interruption, and security drills.

Exit: signed release artifacts pass install/upgrade/rollback/uninstall acceptance on supported targets.

## Stable API contracts to add

### Runtime bootstrap

Returns mode, current identity, allowed product capabilities, API version, application version, and health state. It must not reveal storage paths or secrets.

### Error envelope

```json
{
  "code": "credential.invalid",
  "message": "LinkedIn credentials need attention.",
  "retryable": false,
  "action": "open_connections",
  "return_route": "/workflows",
  "correlation_id": "redacted-safe-id"
}
```

### Health/readiness

Separately reports process liveness, startup/migration readiness, database, runtime state, credential-store availability, RAG, and scheduler status. Public liveness reveals no sensitive detail; full diagnostics requires authentication.

## Test matrix

| Layer | Required coverage |
|---|---|
| Unit | Runtime parsing, paths, stores, credential states, error envelopes |
| Contract | Redis/SQLite state parity; PostgreSQL/SQLite repositories; credential stores |
| Safety | Approval, reject, retry, kill switch, guardrails, cost/rate hard stops |
| Isolation | Reused IDs across users/installations and concurrent state/RAG access |
| Lifecycle | Startup, migration, readiness, crash, bounded restart, graceful/forced stop |
| Packaging | Native clean-machine install and dependency smoke tests |
| UX/e2e | Onboarding, recovery, approvals, updates, backup/restore |
| Release | Signature verification, upgrade preservation, rollback, uninstall semantics |

## Release blockers

- Any safety invariant differs by runtime mode.
- Packaged execution requires user-installed Python, PostgreSQL, or Redis.
- Desktop secrets can fall back to plaintext or enter JavaScript/SQLite/logs.
- A second instance can corrupt or concurrently own local scheduling.
- Migration/update can discard user data without a recoverable backup.
- Server tenant boundaries fail adversarial tests.
- Artifacts or update metadata are unsigned.

## Decision checkpoints

1. After Milestone 2: confirm adapter design before schema/data changes.
2. After Milestone 4: confirm Tauri or invoke the documented Electron fallback.
3. Before beta: confirm supported OS/architecture matrix and run-while-open messaging.
4. Before stable: approve signing, update, rollback, retention, and incident procedures.
