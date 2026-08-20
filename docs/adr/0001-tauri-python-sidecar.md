# ADR 0001: Tauri 2 with a managed Python sidecar

- Status: Accepted for implementation spike
- Date: 2026-08-20

## Context

The product already has a substantial React/Vite UI and a Python/FastAPI backend containing the agent, LLM-routing, tool, approval, memory, and scheduler systems. A desktop rewrite would create two business-logic implementations and increase safety risk.

## Decision

Use Tauri 2 as the native owner process. Bundle the optimized React/Vite frontend and a per-platform frozen FastAPI executable. Tauri owns sidecar launch, authenticated readiness, restart limits, and shutdown.

The sidecar binds only to loopback on an OS-selected port. Tauri supplies a per-launch secret through an inherited pipe rather than argv. Packaged builds do not expose API documentation.

## Consequences

- React code remains the shared UI; Vite is a build-time tool, not an installed server.
- Python business logic remains shared with hosted mode.
- Native CI must build and test the Python executable on every target OS/architecture.
- Rust and platform webview behavior become release concerns.
- Electron remains the fallback only if the Phase 3 spike demonstrates unacceptable webview or native-dependency failures.

## Acceptance evidence

The spike must prove clean-machine installation, authenticated startup, migration, health reporting, bounded crash recovery, graceful exit, and absence of orphan processes on every supported target.
