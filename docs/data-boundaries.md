# Data Boundaries and Ownership

## Ownership model

Server mode owns data by dashboard user. Desktop mode initially has one local owner and one workspace, but retains explicit identifiers so future workspaces do not require another schema rewrite. Identity is injected from trusted context.

## Storage map

| Data | Server | Desktop | Durability / isolation requirement |
|---|---|---|---|
| Domain records and approvals | PostgreSQL | SQLite | Explicit owner/workspace key and foreign keys |
| Working memory | Redis | SQLite state store | Namespaced and TTL-aware |
| Cost/rate counters | Redis | SQLite state store | Atomic and restart-safe |
| Kill switch | Redis | SQLite state store | Durable and checked at execution time |
| Scheduler ownership/claims | Redis | SQLite + native single instance | Atomic idempotency claims |
| RAG | Tenant-scoped files | Installation/workspace files | Versioned manifest and atomic generations |
| Provider secrets | Encrypted DB rows | OS keyring | Never stored in plaintext or frontend state |
| Connection metadata | PostgreSQL | SQLite | Non-secret status/scopes/last-tested/error |
| Logs | Deployment logging | Installation log directory | Redacted, bounded retention |
| Backups | Operator-managed volumes | Installation backup directory | Versioned, validated, user-controlled |

## Desktop layout contract

The native owner supplies an absolute application-data directory. Expected children are:

```text
database/app.sqlite3
state/runtime.sqlite3
rag/<workspace-id>/
logs/
backups/
cache/
config/runtime.json
```

Code must not write packaged production data relative to the repository, executable, or current working directory.

## SQLite contract

- Enable foreign keys and WAL mode.
- Use a bounded busy timeout and transactional writes.
- Back up before applying migrations that can alter user data.
- Test migrations from every supported released schema, not only `create_all`.
- Keep engine-specific SQL in adapters with PostgreSQL and SQLite tests.
- Never use process-memory state as the sole source for approvals, cost/rate limits, kill switch, migrations, or recovery.

## RAG contract

Each workspace owns one namespace for primary and semantic memory. Its manifest records format version, embedding implementation/version, vector dimensions, and current generation. Writes use a cross-platform lock and atomic generation switch. Authoritative records must support rebuilding a corrupt or incompatible index.

## Known boundary defects

Before desktop beta or renewed “fully isolated” product claims:

- add explicit ownership to legacy episodic and semantic records;
- eliminate the physically shared semantic index or make its workspace boundary structural;
- scope processed notification identity by provider and owner;
- namespace draft/thread/approval-session state keys;
- add isolation tests that deliberately reuse external/entity identifiers across owners.

## Retention and deletion

Desktop data persists across upgrades and ordinary uninstall by default. Reset/export/delete operations must enumerate affected stores, require confirmation, stop active jobs, produce an audit event where possible, and report whether recovery remains available from backup.
