# ADR 0002: Explicit server and desktop runtime profiles

- Status: Accepted
- Date: 2026-08-20

## Context

The hosted application depends on PostgreSQL, Redis, session authentication, multi-user administration, and distributed scheduler coordination. A personal desktop installation should not require those services or repeated login. Scattered environment checks would make behavior difficult to reason about and could bypass shared safety controls.

## Decision

Define one immutable runtime profile at process startup:

| Concern | Server | Desktop |
|---|---|---|
| Identity | Session + CSRF + RBAC | Stable local owner + per-launch shell token |
| Database | PostgreSQL | SQLite |
| Runtime state | Redis | Transactional SQLite store |
| Credentials | Encrypted database rows | OS keyring |
| Users | Multi-user administration | One local owner |
| Scheduling | Distributed coordination | Single instance, run while open |

Runtime-varying services are selected through interfaces. Agents, the model router, tool registry, approval gate, kill switch, guardrails, cost/rate policies, and evaluations are shared and cannot be disabled by the runtime profile.

Desktop state lives below an absolute OS application-data path supplied by Tauri. Business code must not derive production paths from the working directory.

## Consequences

- Existing server behavior is the compatibility default.
- Redis cannot be replaced by in-memory dictionaries; desktop safety and recovery state must be durable.
- SQLAlchemy queries and migrations require contract tests on SQLite and PostgreSQL.
- The current shared/entity-only memory boundaries must be repaired before isolation is claimed.
