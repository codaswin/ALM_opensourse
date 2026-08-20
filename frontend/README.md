# AI LinkedIn Manager — Dashboard

React + Vite + TypeScript UI for the [AI LinkedIn Manager](../README.md). The same build runs inside the Tauri desktop shell and as the optional web/VPS dashboard.

| View | Backend resource | What it does |
|------|-------------------|----------------|
| Approval Queue | `GET/POST /approvals/*` | Review every pending gated action (publish/schedule/delete/reply/DM/connection-request) with full argument content shown, approve or reject |
| Self-Learning | `GET/POST /learning/proposals/*`, `POST /learning/reflect` | Review reflection-job proposals, trigger an on-demand reflection run |
| Settings | `GET/PUT /settings/{key}` | View/edit agent settings (e.g. `research_agent.poll_interval`) |
| Cost | `GET /cost` | Today's LLM spend vs. the daily cap |
| Workflows | `POST /workflows/*` | Run research, content, analytics, and engagement workflows |
| Connections | `GET/POST /credentials/*` | Manage integration credentials and connected accounts |
| Brand Voice | `GET/POST /brand-voice/*` | Maintain writing-style profiles |
| Users (server only) | `GET/POST /admin/users` | Administer hosted workspace accounts |

## Run locally

```bash
npm install
cp .env.example .env   # only needed if the backend isn't on http://localhost:8010
npm run dev
```

For browser development, the backend runs separately (`uvicorn app.main:app --reload` from `backend/`) and must allow this dev server's origin via `CORS_ALLOWED_ORIGINS`. The packaged desktop app starts and authenticates its local backend sidecar automatically.

## Build

```bash
npm run build      # tsc -b && vite build -> dist/
npm run preview    # serve the production build locally
```

## Notes

- **Identity**: hosted mode uses the authenticated workspace account; desktop mode uses a stable local-owner identity created for the installation. Approval audit records derive the actor server-side.
- **`approveApproval` vs `rejectApproval` response shapes differ** (`src/types.ts`'s `ToolExecutionResult` vs `ApprovalRequest`) — that's a real asymmetry in `backend/app/main.py`, not a frontend bug: approving actually executes the gated tool and returns its raw result; rejecting just updates the approval record.
- No settings-listing endpoint exists (`memory/settings.py` is a key-by-key store) — the Settings view shows the one known seeded key and offers a lookup box for any other key by name, rather than trying to enumerate all settings.
