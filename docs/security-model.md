# Security Model

## Protected assets

- LinkedIn and LLM-provider credentials
- posts, messages, approvals, schedules, brand voice, and learned memory
- approval identity, execution attempts, idempotency records, and audit events
- model spend and provider rate budgets
- application/update signing keys and update metadata

## Trust boundaries

| Boundary | Rule |
|---|---|
| React UI to API | Every request is authenticated; UI state is never authority |
| Tauri to sidecar | Loopback plus high-entropy per-launch token; port alone is not trusted |
| Agent to model | All calls go through the model router |
| Agent to tool | Inputs pass registry schema validation and sandboxing |
| Tool to external side effect | Approval-required tools execute only through the durable approval gate |
| Backend to credential storage | Secrets never enter frontend storage, ordinary logs, or local SQLite |
| Updater to installation | Artifacts and metadata must verify against pinned signing trust |

## Non-negotiable invariants

1. Only the approval gate can pass `approved=True` to a gated tool.
2. Rejection never executes a tool; retry follows the same gate and idempotency policy.
3. The kill switch is checked immediately before approved external execution.
4. Cost and rate limits fail closed and remain durable across process restart.
5. Runtime mode cannot disable guardrails, safety audits, or evaluations.
6. Tenant/workspace identity comes from trusted request/runtime context, not arbitrary payload fields.

## Desktop threat controls

- Bind only to `127.0.0.1` using an unpredictable port.
- Transfer the launch token by inherited stdin/pipe, not command-line arguments or files.
- Allow only the packaged application origin and a narrow Tauri capability set.
- Disable API documentation and reject browser requests without the launch token.
- Redact credentials, cookies, CSRF values, launch tokens, provider responses, and sensitive post/message content according to log policy.
- Refuse insecure OS-keyring fallback.
- Preserve data on ordinary uninstall by default; require explicit confirmation for reset/delete.
- Back up before schema or RAG-format migration and surface recovery rather than silently resetting.

## Hosted threat controls

Preserve HttpOnly/Secure/SameSite cookies, rotating CSRF tokens, RBAC, login throttling, CORS allowlists, encrypted credential rows, tenant-scoped queries, and distributed scheduler locking. Repair legacy entity-only memory and notification identifiers before advertising complete isolation.

## Required verification

- safety static audit and approval behavior tests on every build matrix;
- cross-user and cross-installation adversarial isolation tests;
- secret/redaction and unauthenticated-loopback tests;
- sidecar orphan/crash/restart tests;
- signed update, rollback, backup, and restore drills;
- dependency vulnerability, SBOM, and license checks before release.
