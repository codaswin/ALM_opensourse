# 🤖 AI LinkedIn Manager

> A multi-agent system that manages a professional's LinkedIn presence end-to-end — drafting on-brand posts, engaging with the feed, replying to comments and DMs, tracking connections, reporting on performance, and researching AI/agentic-AI developments across six independent sources — with every public, irreversible, or third-party-contacting action gated behind explicit human approval. No exceptions, verified by test.

Free and open source (MIT). Run it as a **desktop app** on your own machine with your own credentials, or **self-host** it on a VPS for a team — same codebase, same safety guarantees, either way. Nobody's server, nobody's API keys, nobody's data but yours.

<p align="center">
  <em>5 runtime agents · 19 tools (6 require human approval) · 6 research sources · 592 tests</em>
</p>

---

## Table of Contents

1. [What This Actually Is](#what-this-actually-is)
2. [Install](#install)
3. [Design Philosophy](#design-philosophy)
4. [System Architecture](#system-architecture)
5. [The 5 Runtime Agents](#the-5-runtime-agents)
6. [The Multi-Source Research System](#the-multi-source-research-system)
7. [Safety & the Human-Approval Gate](#safety--the-human-approval-gate)
8. [Tool Registry](#tool-registry)
9. [Memory Architecture](#memory-architecture)
10. [RAG Pipeline](#rag-pipeline)
11. [Eval Harness](#eval-harness)
12. [Self-Learning Loop](#self-learning-loop)
13. [End-to-End Workflows](#end-to-end-workflows)
14. [A Note on "Animations"](#a-note-on-animations)
15. [Tech Stack](#tech-stack)
16. [Project Structure](#project-structure)
17. [Model Routing & Cost Controls](#model-routing--cost-controls)
18. [Environment Variables](#environment-variables)
19. [Desktop Development](#desktop-development)
20. [Self-Hosted Development](#self-hosted-development)
21. [Dashboard (Frontend)](#dashboard-frontend)
22. [Testing & Validation Gates](#testing--validation-gates)
23. [Project Status](#project-status)
24. [Roadmap](#roadmap)
25. [How This Was Built](#how-this-was-built)
26. [Contributing](#contributing)
27. [License](#license)

---

## What This Actually Is

This is **not** a chatbot wrapper. It's a small society of narrowly-scoped agents, each with one job, a fixed toolset, and a hard-coded escalation rule, coordinated through a single choke-point agent loop. Nothing in this system can post, delete, message, or connect on a real person's behalf without a human explicitly clicking "approve" on the exact content that would go out.

Concretely, it:

- **Decides what to post about** by grounding topic selection in retrieved research, brand voice, and the last 30 days of published posts (Content Strategist)
- **Writes full post drafts** in the user's brand voice, self-scores its own confidence, and either queues the draft for approval or flags it "needs human rewrite" (Content Writer)
- **Monitors comments, DMs, and connection requests**, drafts replies, and screens every one for five categories of sensitive topics before it ever reaches a draft (Engagement)
- **Produces a weekly performance digest** and flags stale/underperforming/risky posts for possible deletion — a suggestion that *always* routes to a human, regardless of how confident the system is (Analytics & Reporting)
- **Tracks what's happening in AI** across Hacker News, Reddit, GitHub, Product Hunt, RSS feeds, and the general web (X/Twitter optional, off by default) to keep the Content Strategist's topic choices current (Research)

Every one of those five agents shares one rule without exception: **no agent holds a reference to an LLM client and calls it directly.** Every single model call in this entire codebase goes through one function — `harness.loop.run_step()` — which is what makes tracing, cost tracking, retries, and tool-call logging actually enforceable rather than aspirational.

---

## Install

Two ways to run it — same agents, same safety guarantees, same codebase:

|  | **Desktop** | **Self-hosted** |
|---|---|---|
| Best for | One person, on their own computer | A team, or anyone who wants it always-on |
| Runs on | Windows, macOS, Linux | Any VPS/server with Docker |
| Database | SQLite (bundled, no setup) | PostgreSQL |
| State/locks | Local SQLite | Redis |
| Credentials | Your OS's own secure store (Windows Credential Manager / macOS Keychain / Linux Secret Service) | Encrypted database rows |
| Login | None — the app is already yours | Username/password, invite-only accounts |
| You need | Nothing pre-installed | Docker + Docker Compose |

Both modes share every agent, every safety gate, the model router, the tool registry, and the approval queue — nothing about *what* the system will and won't do differs by runtime. See [`docs/architecture.md`](docs/architecture.md), [`docs/security-model.md`](docs/security-model.md), and [`docs/data-boundaries.md`](docs/data-boundaries.md) for the full design.

### Desktop app

The desktop shell is [Tauri](https://tauri.app/) (a Rust-owned window around the same React UI, spawning a frozen Python backend as a local sidecar — see [`docs/desktop-migration-audit.md`](docs/desktop-migration-audit.md) for why Tauri over Electron). It:

- binds its backend to `127.0.0.1` on a random port with a per-launch auth token — nothing is reachable from outside your machine;
- stores your LinkedIn/AI-provider credentials in your OS's own secure credential store, never in a plaintext file;
- uses a local SQLite database and vector index instead of requiring you to install PostgreSQL or Redis;
- requires no login — the app already knows it's yours.

**Signed, downloadable installers aren't published yet** (see [Project Status](#project-status) — this is a genuinely new open-source project, not a promise deferred). Until then, build it yourself:

```bash
git clone https://github.com/codaswin/ALM_opensourse.git
cd ALM_opensourse

python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && npm install && cd ..

# Native prerequisites: Rust (rustup.rs) plus your OS's Tauri toolkit —
# Linux needs WebKitGTK/GTK dev packages, Windows needs the WebView2 SDK
# (usually already present) and Visual Studio Build Tools, macOS needs
# Xcode Command Line Tools. Full list: docs/desktop-development.md.
bash scripts/build-sidecar.sh
npx @tauri-apps/cli@2 build   # or: cargo install tauri-cli, then `cargo tauri build`
```

This produces a native installer under `src-tauri/target/release/bundle/` — a `.AppImage`/`.deb`/`.rpm` on Linux, and the equivalent `.msi`/`.exe` or `.dmg`/`.app` once built on a Windows or macOS machine. First launch walks you through a short local onboarding, then you paste in your own Anthropic/OpenAI and Composio (LinkedIn) credentials on the Connections page — nothing is pre-filled, nothing is shared with anyone else's installation.

### Self-hosted (VPS / server)

For a team, or a workspace you want running even when your laptop is closed:

```bash
git clone https://github.com/codaswin/ALM_opensourse.git
cd ALM_opensourse
cp .env.example .env
# at minimum: set CREDENTIAL_ENCRYPTION_KEY and DASHBOARD_ADMIN_PASSWORD

docker compose up --build
```

Then open `http://localhost:5173` (or your server's address), sign in with the bootstrap admin account, and invite teammates from the Users page — each person gets their own private set of credentials, approvals, brand voice, and automation, invisible to everyone else (own database rows, own cached provider clients, own vector index namespace, own daily cost cap). For a real public deployment with HTTPS, a domain, and Docker secrets instead of a plaintext `.env`, follow [`deploy/README.md`](deploy/README.md).

---

## Design Philosophy

Five decisions shape everything else in this repo:

**1. Approval is structural, not a suggestion.** `requires_approval=True` on a tool isn't a flag some code path checks when convenient — `tools/registry.execute_tool()` refuses to run a gated tool without an explicit `approved=True`, and there is exactly **one function in the entire codebase** permitted to flip that flag: `safety.approval_gate.approve()`. A static audit (`python -m app.safety.audit`) fails the build if that ever stops being true.

**2. Cost-consciousness is a first-class design constraint, not an afterthought.** The Research Agent was originally X (Twitter)-only. X's API got expensive, so it was refactored into six sources — five of which need no paid API key at all (Hacker News, RSS, and DuckDuckGo web search need *nothing*; GitHub and Product Hunt work at generous free tiers). X is still available, just opt-in.

**3. Self-improvement is reviewed, never silent.** The learning loop can auto-apply a retrieval-weight tweak or an additive few-shot example on its own. It can **never** auto-apply a change to a system prompt, the brand-voice profile, a new tool, an approval-gating rule, or a confidence threshold — regardless of how confident the reflection job's own analysis is. That's enforced in code (`proposal_review.submit_proposal()`), not just policy.

**4. Every agent is testable without a live model — even now that a live one exists.** Every agent function takes an injectable `llm_client`, and every one of this repo's tests still runs against a fake; the one real implementation (`model_router.route_and_call`, wired to Anthropic or OpenAI for primary/cheap and Hermes/vLLM for the worker tier) is itself just another value that fits the same `llm_client` slot. That was a deliberate sequencing choice: build and prove the harness, the safety gates, and the eval/learning infrastructure first — against fakes — and only then wire in a real model, so "real" never means "suddenly untestable."

**5. Your credentials are yours, structurally, not by convention.** Every LinkedIn/AI-provider/research-source credential belongs to one owner — the desktop installation, or one self-hosted dashboard user — never a shared process-wide value. `resolve_credential()` has no fallback: a value only exists for the identity that saved it (`app/tenancy/`). That's what makes both distribution models the same codebase — desktop's "one local owner" and self-hosted's "many invited users" are the same ownership model at different scale, not a fork.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Runtime["🎯 5 Runtime Agents"]
        direction LR
        CS["Content<br/>Strategist"]
        CW["Content<br/>Writer"]
        EN["Engagement"]
        AN["Analytics &<br/>Reporting"]
        RE["Research"]
    end

    subgraph Harness["⚙️ Harness — the single choke point"]
        RunStep["run_step()<br/><i>the ONLY function allowed to call an LLM</i>"]
        Stop["stopping_conditions.py<br/>budget / iteration / escalation"]
    end

    subgraph Safety["🛡️ Safety Layer"]
        Guard["guardrails.py<br/>5 refusal-topic detectors"]
        Gate["approval_gate.py<br/>the ONLY path to execute a gated tool"]
        Kill["kill_switch.py"]
        Cap["cost_cap.py<br/>$/day + per-action rate caps"]
    end

    subgraph Tools["🔧 19 Tools (registry.py)"]
        direction LR
        ReadTools["13 read/internal-write<br/>no approval needed"]
        WriteTools["6 write tools<br/>ALWAYS require approval"]
    end

    subgraph Memory["🧠 Memory"]
        Working["Working (Redis)"]
        Episodic["Episodic (Postgres)"]
        Semantic["Semantic (FAISS)"]
    end

    subgraph Research6["🔍 6 Research Sources"]
        direction LR
        HN[Hacker News]
        RD[Reddit]
        GH[GitHub]
        PH[Product Hunt]
        RSS[RSS Feeds]
        WEB[Web / DuckDuckGo]
        X["X — optional"]
    end

    subgraph Quality["📊 Phase 3 — Quality"]
        Eval["Eval Harness<br/>golden sets + LLM judge<br/>+ 5% regression gate"]
        Learn["Self-Learning Loop<br/>feedback → reflection → review queue"]
    end

    LinkedIn(("LinkedIn<br/>via Composio"))
    Human{{"👤 Human"}}

    Runtime --> RunStep
    RunStep --> Stop
    Runtime --> Tools
    RE --> Research6
    WriteTools -.->|blocked until| Gate
    Gate -->|approve/reject| Human
    Gate -->|approved only| LinkedIn
    ReadTools --> LinkedIn
    Runtime --> Guard
    Guard -->|refusal topic| Human
    Runtime --> Memory
    Runtime --> Eval
    Eval --> Learn
    Learn -.->|human review| Human

    style Gate fill:#7c3aed,color:#fff
    style Guard fill:#dc2626,color:#fff
    style RunStep fill:#0891b2,color:#fff
    style Human fill:#16a34a,color:#fff
```

The shape to internalize: **every arrow that touches LinkedIn or a real third party passes through the purple approval gate first.** There is no other path.

---

## The 5 Runtime Agents

| # | Agent | Model Tier | Tools It Can Call | Escalation Condition |
|---|-------|-----------|--------------------|-----------------------|
| 1 | **Content Strategist** | Cheap (planning task) | `search_knowledge_base` | None — output is an internal brief, never user-facing |
| 2 | **Content Writer** | Primary | `search_knowledge_base`, `draft_post` | Brand-voice confidence < **0.75** → `needs_human_rewrite`, never queued |
| 3 | **Engagement** | Worker (triage) / Primary (draft) | `get_linkedin_notifications`, `search_knowledge_base`, `like_post`, `reply_to_comment`, `reply_to_dm`, `send_connection_request` | Sensitive-topic match **or** confidence < 0.75 → escalate, no draft produced |
| 4 | **Analytics & Reporting** | Cheap (digest) | `generate_analytics_report`, `search_knowledge_base`, `delete_post` | `delete_post` suggestions **always** escalate, unconditionally |
| 5 | **Research** | Worker (triage) / Primary (digest, synthesis) | 6 source tools + `save_research_note`, `search_knowledge_base` | None — read-only, informational only |

### 1. Content Strategist Agent

Decides **what** to post about, never writes a word of copy. Pulls the content calendar, RAG-retrieved trending topics (including the Research Agent's findings), and the last 30 days of published posts; de-duplicates against recently-covered topics using a keyword-overlap heuristic (falls back to the full retrieved set if *everything* overlaps, rather than handing the next agent nothing). Output is one structured `PostBrief`: `{topic, angle, format, target_publish_date}`.

### 2. Content Writer Agent

Turns a `PostBrief` into full post copy, grounded in the brand-voice/style-guide RAG source, past posts, and industry news — then **self-scores its own confidence** that the draft matches brand voice. There is no partial credit: `confidence >= 0.75` → submitted to the human approval queue with either `publish_post` or `schedule_post` (chosen automatically based on whether the brief carries a `target_publish_date`); below that → returned as `needs_human_rewrite`, never touching the approval queue at all.

### 3. Engagement Agent

Watches comments, DMs, and connection requests. For every notification, the **first** check — before any drafting happens — is a regex-based refusal-topic scan (`guardrails.matches_refusal_topic`) across five categories: political endorsements, health/financial/legal advice, disparagement of a named individual or competitor, engagement-bait/misinformation, and impersonation requests. A match means immediate escalation with zero draft generated. If clean, it drafts a reply grounded in past comment/DM threads and brand voice, scores confidence, and either escalates (< 0.75) or queues for approval. `like_post` is the one action in this agent's toolkit that executes directly — it's rate-capped and reversible, not identity-risking.

### 4. Analytics & Reporting Agent

Produces a weekly digest (impressions, engagement rate, follower delta — all deterministic, pulled straight from stored data, never re-derived by the LLM) and uses the model only for the judgment call: which posts look underperforming, stale, or reputationally risky enough to flag. `suggest_deletion()` has **no confidence parameter at all** — there's no code path by which a "the model is very sure" argument could ever skip the approval queue for a delete action, and the approval prompt is required to carry the full post content, publish date, and engagement stats (never a bare post ID).

### 5. Research Agent

The most heavily reworked piece of this system — see the next section.

---

## The Multi-Source Research System

**Origin story:** this agent started as an X (Twitter)-only research feed. X's API is expensive at any real volume, so it was refactored into a modular, six-source system where X is available but never the default.

```mermaid
flowchart LR
    Query(["Research query,<br/>e.g. 'AI agents'"])

    subgraph Selection["1️⃣ Source Selection — cheap keyword heuristic, NOT an LLM call"]
        Rule1["open-source/framework/tool<br/>→ GitHub, HN, Reddit, Web"]
        Rule2["product/SaaS/launch<br/>→ Product Hunt, HN, Web, Reddit"]
        Rule3["reaction/opinion/discussion<br/>→ Reddit, HN, GitHub, Web"]
        Rule4["announcement/coverage/news<br/>→ RSS, Web, HN"]
        Default["no match →<br/>HN, Web, GitHub, Reddit"]
    end

    subgraph Fetch["2️⃣ Concurrent Fetch — asyncio.gather, one failure never sinks the run"]
        direction TB
        HN2["🟠 Hacker News<br/>Firebase API, no key"]
        RD2["🔴 Reddit<br/>OAuth2 client-credentials"]
        GH2["⚫ GitHub<br/>REST search, optional token"]
        PH2["🟣 Product Hunt<br/>GraphQL v2"]
        RSS2["🟢 RSS/Atom<br/>feedparser, 8 default feeds"]
        WEB2["🔵 DuckDuckGo<br/>via ddgs, no key"]
    end

    Normalize["3️⃣ Normalize<br/>→ one ResearchResult schema for all six"]
    Dedupe["4️⃣ Dedupe<br/>canonical URL + title-similarity (Jaccard ≥ 0.6)<br/>merges engagement, tracks also_seen_on"]
    Rank["5️⃣ Rank<br/>35% relevance + 25% recency + 15% source-quality<br/>+ 10% engagement + cross-source bonus"]
    Synth["6️⃣ Synthesize<br/>LLM call via run_step()<br/>citations built by CODE, never the LLM"]
    Package(["ResearchPackage:<br/>executive_summary, key_findings,<br/>interesting_angles, citations,<br/>source_coverage"])

    Query --> Selection
    Selection --> Fetch
    HN2 & RD2 & GH2 & PH2 & RSS2 & WEB2 --> Normalize
    Normalize --> Dedupe --> Rank --> Synth --> Package

    style Selection fill:#1e3a5f,color:#fff
    style Fetch fill:#1e3a5f,color:#fff
    style Synth fill:#0891b2,color:#fff
```

### The 6 sources

| Source | Auth | Cost | What it's good for |
|--------|------|------|---------------------|
| **Hacker News** | None | Free | Top/new/best/show/ask/job stories, optional top-comment context |
| **Reddit** | OAuth2 client-credentials | Free | Subreddit-aware search with keyword-based subreddit inference (AI → r/LocalLLaMA, r/MachineLearning; startups → r/startups, r/SaaS; falls back to sitewide search) |
| **GitHub** | Optional token (works unauthenticated) | Free | Repository discovery — stars, forks, language, topics, recent activity |
| **Product Hunt** | GraphQL v2 token | Free | Recently-launched products, filtered client-side by keyword since PH's API has no free-text search |
| **RSS/Atom** | None | Free | 8 built-in feeds (TechCrunch, VentureBeat, HN Best/Newest, Y Combinator, MIT Tech Review, Google AI Blog, Hugging Face) — fully overridable via `RSS_FEEDS` |
| **Web (DuckDuckGo)** | None | Free | General web search via the `ddgs` package — zero configuration |
| **X (Twitter)** | Composio, read-only | Paid API | **Optional only** — never chosen by the selection heuristic, reachable only via explicit `sources=["x", ...]` |

### Every source is isolated from every other

```python
async def _fetch_source(source: str, query: str, limit: int) -> list[ResearchResult]:
    adapter = ALL_SOURCES[source]
    try:
        return await adapter(query, limit)
    except Exception as exc:
        logger.warning("research_source_adapter_failed", source=source, error=str(exc))
        return []   # one dead source degrades gracefully — never sinks the run
```

Reddit's credentials aren't configured yet in most fresh setups? No problem — that source silently returns `[]`, gets logged, and the other five keep working. This was proven in production use during development: Product Hunt and web-search feeds both hit real transient failures (missing tokens, HTTP redirects) during testing, and neither ever took down a research run.

### Ranking is never "sort by popularity"

```python
score = (0.35 * relevance) + (0.25 * recency) + (0.15 * source_quality) + (0.10 * engagement) + cross_source_bonus
```

A viral-but-irrelevant Reddit thread loses to a quiet, on-topic RSS announcement from an official blog — relevance, recency, and source trust deliberately outweigh raw engagement 9-to-1.

---

## Safety & the Human-Approval Gate

```mermaid
sequenceDiagram
    participant Agent as Runtime Agent
    participant Guard as guardrails.py
    participant Registry as tools/registry.py
    participant Gate as approval_gate.py
    participant DB as Postgres
    participant Human as 👤 Human
    participant LinkedIn as LinkedIn (via Composio)

    Agent->>Guard: matches_refusal_topic(text)?
    alt sensitive topic matched
        Guard-->>Agent: topic name
        Agent->>Human: escalate_to_human() — no draft generated
    else clean
        Agent->>Agent: draft + self-score confidence
        alt confidence < 0.75
            Agent->>Human: escalate — needs_human_rewrite
        else confidence >= 0.75
            Agent->>Registry: execute_tool(name, args, approved=False)
            Registry-->>Registry: requires_approval? BLOCKED without approved=True
            Agent->>Gate: submit_for_approval(tool_name, arguments, reason, confidence)
            Gate->>DB: INSERT pending approval request
            Gate-->>Agent: {status: "pending", id}
            Human->>Gate: approve(approval_id) — the ONLY function<br/>allowed to call execute_tool(..., approved=True)
            Gate->>Registry: execute_tool(tool_name, args, approved=True)
            Registry->>LinkedIn: the real action finally happens
        end
    end
```

### The five refusal topics (regex-matched, `guardrails.py`)

| Topic | Example trigger |
|-------|------------------|
| Political endorsement | *"who should I vote for..."* |
| Health/financial/legal advice | *"what medication should I take"*, *"should I invest in..."* |
| Disparagement | *"bash our competitor"*, *"worst CEO"* |
| Engagement-bait / misinformation | *"comment yes if..."*, *"unverified claim"* |
| Impersonation | *"pretend to be..."*, *"ghostwrite this as..."* |

### Rate & cost caps

| Cap | Default | Enforced by |
|-----|---------|-------------|
| LLM spend | $10/day | `llmops/cost_tracker.py` |
| Posts | 3/day | `LINKEDIN_API_RATE_LIMIT_POSTS_DAILY` |
| Deletes | 3/day | `LINKEDIN_API_RATE_LIMIT_DELETES_DAILY` |
| Comment/DM replies | 20/day | `LINKEDIN_API_RATE_LIMIT_REPLIES_DAILY` |
| Connection requests | 5/day | `LINKEDIN_API_RATE_LIMIT_CONNECTIONS_DAILY` |
| Likes | 20/day | `LINKEDIN_API_RATE_LIMIT_LIKES_DAILY` |

Plus a kill switch (`safety/kill_switch.py`) that `approve()` checks before executing anything — flip it and every pending approval refuses to execute until it's cleared, system-wide.

A static audit enforces all of this stays true: `python -m app.safety.audit` walks the full tool registry and fails loud if it ever finds a risky tool without a gate.

---

## Tool Registry

19 tools total, 6 requiring human approval:

| Tool | Approval? | Purpose |
|------|:---:|---------|
| `search_knowledge_base` | — | Query the RAG index |
| `get_linkedin_notifications` | — | Poll comments/DMs/connection requests (read-only) |
| `draft_post` | — | Create a queued (unpublished) draft |
| `generate_analytics_report` | — | Summarize stored engagement data |
| `like_post` | — | Like a post (rate-capped, logged, not identity-risking) |
| `search_hackernews` | — | Hacker News research source |
| `search_reddit` | — | Reddit research source |
| `search_github` | — | GitHub research source |
| `search_producthunt` | — | Product Hunt research source |
| `search_rss` | — | RSS/Atom research source |
| `search_web` | — | Web search (DuckDuckGo by default) |
| `search_x_posts` | — | X research source (read-only, optional) |
| `save_research_note` | — | Persist a research finding (internal write only) |
| **`publish_post`** | ✅ | Publish to LinkedIn immediately |
| **`schedule_post`** | ✅ | Queue a future publish |
| **`delete_post`** | ✅ | Delete a published post — irreversible |
| **`reply_to_comment`** | ✅ | Public reply, attributed to the user |
| **`reply_to_dm`** | ✅ | Private message to a real third party |
| **`send_connection_request`** | ✅ | Connection request — ToS-sensitive |

Every tool has a Pydantic input schema and every call is sandboxed with a timeout. Harness-managed calls retain full input/output/latency/cost records, while direct registry executions emit structured status and latency logs.

---

## Memory Architecture

```mermaid
flowchart LR
    subgraph Working["Working Memory — Redis"]
        W1["Current draft in progress"]
        W2["Notification thread being triaged"]
        W3["Session approval-queue state"]
    end
    subgraph Episodic["Episodic Memory — Postgres"]
        E1["12 months of posts + engagement stats"]
        E2["90 days of comment/DM threads<br/>+ resolution (auto/edited/escalated)"]
    end
    subgraph Semantic["Semantic Memory — FAISS"]
        S1["Brand voice / tone profile"]
        S2["Per-connection relationship context"]
        S3["Standing research interests"]
    end
    Note["Every write carries `source` + `confidence`<br/>— CLAUDE.md forbids untraceable memory"]
    Working -.-> Note
    Episodic -.-> Note
    Semantic -.-> Note
```

Retention: episodic post/engagement data kept 12 months then archived; DM/comment thread **content** (not metadata) purged after 90 days unless the user flags it important — LinkedIn ToS and privacy-driven, not arbitrary.

---

## RAG Pipeline

| Source | Type | Update Frequency | Chunking |
|--------|------|-------------------|----------|
| Past LinkedIn posts | Structured | On publish | 1 chunk/post |
| Brand voice / style guide | Document | Static | 500 tokens, semantic split |
| Industry news / trending topics | Document | Daily | 1 chunk/article |
| Comment/DM threads | Q&A pairs | Continuous | 1 chunk/thread |
| Research notes (multi-source) | Structured | Per research run | 1 chunk/note, deduped |

Each desktop installation and hosted user gets an isolated FAISS-backed `VectorStore`. Ingestion is idempotent by `(source_type, source_id)` — re-ingesting an edited document evicts its old chunks before adding fresh ones, so the index never silently accumulates duplicates.

---

## Eval Harness

```mermaid
flowchart TB
    Golden["📋 Golden Sets<br/>20 post cases + 15 reply cases<br/>(starter data — swap in your real curated<br/>50+30 set with zero code changes)"]
    Agents["Real agents:<br/>content_writer.write_post()<br/>engagement.handle_notification()"]
    Metrics["Deterministic metrics<br/>must_avoid_check · escalation_precision"]
    Judge["LLM-as-judge (via run_step)<br/>brand_voice_fidelity · groundedness · reply_appropriateness"]
    Baseline{{"baseline.json"}}
    Gate{"Δ > 5%?"}
    Pass(["✅ ship"])
    Fail(["❌ block — PRP regression policy"])

    Golden --> Agents
    Agents --> Metrics
    Agents --> Judge
    Metrics --> Baseline
    Judge --> Baseline
    Baseline --> Gate
    Gate -->|no| Pass
    Gate -->|yes| Fail

    style Fail fill:#dc2626,color:#fff
    style Pass fill:#16a34a,color:#fff
```

- **`must_avoid_check`** — deterministic phrase-ban check against `must_avoid` fields declared right in the golden set
- **`escalation_precision`** — recall (did it escalate when it should?) and precision (did it over-escalate?) computed purely from expected vs. actual behavior, no judge needed
- **LLM judge** — scores brand-voice fidelity and groundedness 1-5, bias-aware (no length bias, no position bias — one candidate scored at a time against fixed written criteria)
- **First run establishes the baseline** rather than failing outright — there's nothing to regress against yet
- 15 of the 15 reply cases are independently cross-checked against the *real* `guardrails.matches_refusal_topic()` regex, not just trusted to LLM judgment — a dedicated test enforces this stays true

Run it: `pytest backend/evals -v --tb=short`

---

## Self-Learning Loop

```mermaid
flowchart LR
    Signal1["👍 Approved"] & Signal2["👎 Rejected"] & Signal3["✏️ Edited"] & Signal4["📈 Engagement<br/>outcome (7-day lag)"] --> Capture["feedback.py<br/>capture_feedback()"]
    Capture --> DB[(Feedback table)]
    DB -->|"≥ 5 negative signals<br/>in the window"| Reflect["reflection_job.py<br/>run_reflection() via run_step()"]
    Reflect --> Classify{"change_type?"}
    Classify -->|retrieval_weight<br/>few_shot_example<br/>AND confidence ≥ 0.8| Auto["✅ auto_applied<br/>+ full audit log"]
    Classify -->|system_prompt<br/>brand_voice_profile<br/>new_tool<br/>approval_gating_rule<br/>confidence_threshold<br/>— ANY confidence| Review["⏸️ pending human review<br/>— NEVER auto-applies, unconditionally"]
    Classify -->|unrecognized type| Review
    Review --> Human2["👤 approve_proposal() / reject_proposal()"]

    style Auto fill:#16a34a,color:#fff
    style Review fill:#7c3aed,color:#fff
```

The hard line, verified by a parametrized test at **confidence = 1.0**: a `system_prompt` or `safety_threshold` proposal never auto-applies, no matter how sure the reflection job's own analysis claims to be. That's exactly the case a self-modifying system must never trust itself on.

| What can auto-apply | What always needs a human |
|---|---|
| Retrieval ranking weight tweaks | System prompt changes |
| Additive few-shot examples | Brand-voice profile changes |
| *(only at ≥ 0.8 confidence)* | New tools |
| | Approval-gating rule changes |
| | Confidence threshold changes |

---

## End-to-End Workflows

### Post creation, from idea to LinkedIn

```mermaid
sequenceDiagram
    autonumber
    participant RAG as RAG Index
    participant CS as Content Strategist
    participant CW as Content Writer
    participant Gate as Approval Gate
    participant Human as 👤 Human
    participant LI as LinkedIn

    CS->>RAG: retrieve(trending topics + last 30 days of posts)
    CS->>CS: dedupe against recently-covered topics
    CS->>CW: PostBrief {topic, angle, format, date}
    CW->>RAG: retrieve(brand voice + past posts + news)
    CW->>CW: draft + self-score confidence
    alt confidence < 0.75
        CW-->>Human: needs_human_rewrite (never queued)
    else confidence >= 0.75
        CW->>Gate: submit_for_approval(publish_post or schedule_post)
        Gate-->>Human: pending approval, full draft shown
        Human->>Gate: approve()
        Gate->>LI: publish/schedule — the only moment anything goes public
    end
```

### Multi-source research, in one call

```mermaid
sequenceDiagram
    autonumber
    participant Caller
    participant Pipeline as research_pipeline.research()
    participant HN as Hacker News
    participant GH as GitHub
    participant PH as Product Hunt
    participant RSS as RSS
    participant RD as Reddit

    Caller->>Pipeline: research("AI agents")
    par concurrent — one failure isolated
        Pipeline->>HN: fetch(query, limit)
        Pipeline->>GH: fetch(query, limit)
        Pipeline->>PH: fetch(query, limit)
        Pipeline->>RSS: fetch(query, limit)
        Pipeline->>RD: fetch(query, limit)
    end
    HN-->>Pipeline: results (or [] on failure)
    GH-->>Pipeline: results
    PH-->>Pipeline: results (or [] — e.g. missing token)
    RSS-->>Pipeline: results
    RD-->>Pipeline: results
    Pipeline->>Pipeline: dedupe (URL + title similarity)
    Pipeline->>Pipeline: rank (relevance/recency/quality/engagement)
    Pipeline-->>Caller: normalized, ranked list of dicts
```

### Weekly digest → delete suggestion (never auto-executed)

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Weekly Trigger
    participant AA as Analytics Agent
    participant Tool as generate_analytics_report
    participant Gate as Approval Gate
    participant Human as 👤 Human

    Cron->>AA: generate_weekly_digest()
    AA->>Tool: execute_tool() — deterministic stats, no LLM
    AA->>AA: LLM judgment: which posts look stale/risky?
    alt post flagged
        AA->>Gate: suggest_deletion() — NO confidence param exists
        Gate-->>Human: full post content + publish date + engagement stats
        Note over Gate,Human: never a bare post ID.<br/>never skipped for "obviously fine."
        Human->>Gate: approve or reject
    end
```

---

## A Note on "Animations"

Being upfront: a plain `README.md` rendered on GitHub can't run real animation — no JS, no CSS transitions, no live motion. What it *can* do natively is render [Mermaid](https://mermaid.js.org/) diagrams, which is why this document leans on them heavily above rather than static ASCII art or (worse) a fabricated animated GIF I have no way to actually produce or verify renders correctly. Every diagram in this README is real, valid Mermaid syntax that GitHub will render as an interactive-feeling SVG in the actual repo view. If you want true animation (a recorded terminal session of the eval suite running, a GIF of the approval-queue UI once one exists), that's a good candidate for a `/docs/media` folder with real captured assets — nothing here should be treated as a placeholder for that.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Orchestration | Custom typed Python harness with specialized agents | Keeps the agent boundaries, tracing, budgets, and approval contracts explicit |
| Inference (primary) | Anthropic Claude or OpenAI (your own key, either provider) | Hosted, strong generation quality |
| Inference (worker) | Hermes via vLLM (self-hosted, optional) | Cheap/fast for high-volume triage |
| RAG | FAISS, one isolated index per user/installation | No KG layer for MVP |
| Serving | FastAPI (`app/main.py`) | Settings, approval queue, learning queue, cost, health, diagnostics |
| Desktop shell | [Tauri 2](https://tauri.app/) (Rust) + the same React UI | Owns the frozen Python sidecar's lifecycle, loopback auth, native window — no Electron/Node/Chromium runtime |
| Backend packaging | PyInstaller (frozen sidecar binary, one per OS) | Desktop users never install Python themselves |
| Frontend | React + Vite + TypeScript (`frontend/`) | Shared UI for the Tauri desktop shell and the self-hosted dashboard |
| Scheduling | APScheduler | Reflection, research, engagement, retention, and approved publishing jobs |
| Database | Desktop: SQLite (WAL mode); Server: PostgreSQL | Local-first defaults, same SQLAlchemy models on both engines |
| Runtime state / locks | Desktop: SQLite; Server: Redis | Working memory, rate/cost counters, kill switch, scheduler locks |
| Credential storage | Desktop: your OS's native keyring (Credential Manager/Keychain/Secret Service); Server: encrypted database rows | Never plaintext, never in the frontend bundle, never shared between installations or users |
| LinkedIn integration | Composio | Auth, token refresh, low-level rate limits offloaded |
| X integration | Composio, read-only scope | Optional research source only |
| Web search | `ddgs` (DuckDuckGo) | No API key, swappable via `WebSearchProvider` interface |
| RSS parsing | `feedparser` | Handles RSS 2.0 / Atom / RDF dialect variance |
| Testing | pytest + pytest-asyncio + pytest-cov | 592 tests |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                # FastAPI app — settings/approvals/learning-queue/cost/health/diagnostics/backup
│   ├── agents/                 # The 5 runtime agents + research_pipeline/sources/schema
│   ├── harness/                 # run_step() — the sole LLM choke point, state machine, stopping conditions
│   ├── tools/                  # 19 registered tools + sandbox + rate limiting + Composio client + connection_test.py
│   ├── memory/                 # working / episodic / semantic stores + platform_credentials.py
│   ├── rag/                    # ingestion + retrieval (installation/user-isolated FAISS, cross-platform locking)
│   ├── context/                 # token-budget assembly + compaction
│   ├── safety/                  # guardrails, approval gate, kill switch, cost cap, audit CLI
│   ├── llmops/                   # model router (+ live route_and_call), anthropic/openai/hermes clients, tracer
│   ├── learning/                  # feedback capture, reflection job, proposal review queue, scheduler
│   ├── tenancy/                    # per-request/per-job user context, per-user credential overlay, RAG paths
│   ├── runtime.py                   # RuntimeMode.DESKTOP vs .SERVER — the one immutable capability boundary
│   ├── application_paths.py          # desktop app-data directory layout
│   ├── credential_store.py            # OS-keyring adapter (desktop) — never plaintext
│   ├── backup.py                       # desktop backup create/list (SQLite + RAG snapshot)
│   └── models/                          # SQLAlchemy models (approvals, feedback, proposals, settings, episodes)
├── evals/                    # golden sets, metrics, LLM judge, regression-gate runner
└── tests/                    # unit and integration tests for everything above

frontend/
├── src/
│   ├── api.ts                # typed fetch client for every backend endpoint
│   ├── types.ts               # response shapes, mirrors backend/app/main.py exactly
│   └── views/                   # workflows, approvals, connections, brand voice, learning, settings,
│                                 # cost, diagnostics, users
└── README.md                 # frontend-specific setup/build docs

src-tauri/
├── src/lib.rs                # spawns the sidecar, per-launch token, process-group cleanup on exit
├── tauri.conf.json           # bundle config, icons, window, CSP
├── icons/                    # native app icons (all platforms)
└── binaries/                 # frozen per-OS sidecar, built by scripts/build-sidecar.sh (git-ignored)

docs/
├── architecture.md, security-model.md, data-boundaries.md   # current-state design docs
├── desktop-development.md, packaging.md, releasing.md        # build/release instructions
└── desktop-migration-audit.md, desktop-implementation-status.md   # how the desktop shell got here
```

---

## Model Routing & Cost Controls

Every `(agent, step)` pair resolves to exactly one tier — never hardcoded elsewhere, always through `llmops/model_router.route()`:

| Agent | Step | Tier | Why |
|-------|------|:---:|-----|
| Content Strategist | plan | Cheap | Planning/routing, not generation |
| Content Writer | draft | **Primary** | Generation quality matters |
| Engagement | triage | Worker | High-volume, low-stakes |
| Engagement | draft | **Primary** | Reply quality matters |
| Analytics | summarize | Cheap | Digest summarization |
| Research | triage | Worker | High-volume post filtering |
| Research | digest | **Primary** | Final write-up quality |
| Research | synthesize | **Primary** | Multi-source synthesis |
| Evals | judge | **Primary** | Gates ship/no-ship decisions |
| Learning | reflect | **Primary** | Infrequent, high-stakes proposals |

---

## Environment Variables

**Only used in self-hosted mode.** The desktop app is configured entirely by its own onboarding UI and the OS keyring — it never reads `.env`. `python-dotenv` loads `.env` automatically for self-hosted mode; nothing else to wire up. See `.env.example` at the repo root for the complete, currently-accurate list.

Two different kinds of variable live in `.env`, and mixing them up is the most common setup mistake:

**Deployment-level** — one value for the whole server, set once in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
VECTOR_DB_PATH=./data/faiss_index
CREDENTIAL_ENCRYPTION_KEY=       # required before saving anyone's Connections credentials
DASHBOARD_ADMIN_USERNAME=admin # bootstrap user, created only when absent
DASHBOARD_ADMIN_PASSWORD=       # required; provide through a secret manager
SESSION_COOKIE_SECURE=true      # false only for local HTTP development
SESSION_TTL_HOURS=12
APPROVAL_MAX_ATTEMPTS=3
APPROVAL_EXECUTION_LEASE_SECONDS=900
HERMES_ENDPOINT=http://localhost:8001/v1   # self-hosted worker model, shared by the whole deployment
LLM_COST_BUDGET_DAILY_USD=10               # each user's own daily cap, same number for everyone

# --- Rate caps (per user, per day) ---
LINKEDIN_API_RATE_LIMIT_POSTS_DAILY=3
LINKEDIN_API_RATE_LIMIT_DELETES_DAILY=3
LINKEDIN_API_RATE_LIMIT_REPLIES_DAILY=20
LINKEDIN_API_RATE_LIMIT_CONNECTIONS_DAILY=5
LINKEDIN_API_RATE_LIMIT_LIKES_DAILY=20
```

**Per-user — do not put these in `.env`.** Anthropic/OpenAI/Composio keys and every research-source credential (Reddit, GitHub, Product Hunt) belong to the individual dashboard user, not the deployment, and are pasted through the **Connections page** after signing in. `resolve_credential()` (`app/tenancy/credentials.py`) has zero fallback to `os.environ` for any of these — a value only exists for a user if that user saved it through Connections, full stop. `.env.example` still lists `ANTHROPIC_API_KEY=`/`COMPOSIO_API_KEY=`/etc. as reference placeholders (so you know the field names Connections expects), but setting them in `.env` has **no effect** on the running app; the only working path is Connections.

Hacker News, RSS, and DuckDuckGo web search work with **zero credentials, for anyone** — they're not gated behind Connections at all.

---

## Desktop Development

```bash
git clone https://github.com/codaswin/ALM_opensourse.git
cd ALM_opensourse

python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# run the full test suite (no live credentials needed — everything runs on fakes)
python -m pytest backend/tests backend/evals -v
ruff check backend
mypy backend/app --ignore-missing-imports
PYTHONPATH=backend python -m app.tools.registry --validate-all-schemas
PYTHONPATH=backend python -m app.safety.audit

# run the desktop shell in dev mode (hot-reloading React + a live sidecar)
bash scripts/build-sidecar.sh
npx @tauri-apps/cli@2 dev   # or: cargo install tauri-cli, then `cargo tauri dev`
```

To produce an actual installer instead of a dev session, see [Install → Desktop app](#desktop-app) and [`docs/packaging.md`](docs/packaging.md). Full native-prerequisite list per OS: [`docs/desktop-development.md`](docs/desktop-development.md).

---

## Self-Hosted Development

```bash
git clone https://github.com/codaswin/ALM_opensourse.git
cd ALM_opensourse

cp .env.example .env
# fill in at minimum: CREDENTIAL_ENCRYPTION_KEY, DASHBOARD_ADMIN_PASSWORD
# (Anthropic/OpenAI/Composio/research-source keys go through the Connections
# page after you sign in, not .env — see Environment Variables above)

python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt

# run the full test suite from the repo root (no live credentials needed — everything runs on fakes)
python -m pytest backend/tests backend/evals -v

# run static checks and safety/tool audits
ruff check backend
mypy backend/app --ignore-missing-imports
PYTHONPATH=backend python -m app.tools.registry --validate-all-schemas
PYTHONPATH=backend python -m app.safety.audit

# run the API server
cd backend
uvicorn app.main:app --reload
# → http://localhost:8000/docs for interactive API docs (settings, approval
#   queue, learning-proposal queue, cost summary, health, diagnostics)

# in a second terminal — the dashboard
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

Without any provider key configured, agents still run in tests (against fakes) but any endpoint that triggers a real model call (e.g. `/learning/reflect`) fails loudly with a structured error rather than pretending to succeed.

For a local production-like stack (PostgreSQL + Redis + built backend/frontend, no manual service setup), use Docker Compose from the repo root:

```bash
docker compose up --build
```

The backend container runs `alembic upgrade head` before starting Uvicorn. Runtime table creation is disabled by default; set `AUTO_CREATE_SCHEMA=true` only for isolated local or test databases. Docker Compose persists the generation-based FAISS store in the `vector_data` volume.

For a public VPS deployment with Caddy-managed HTTPS, private database
networking, Docker secrets, and automated backups, follow
[`deploy/README.md`](deploy/README.md).

---

## Dashboard (Frontend)

A React + Vite + TypeScript single-page app (`frontend/`) — no component framework, no state-management library, no router; `useState` per view is enough for a review-and-decide tool. The exact same build runs two ways: embedded in the Tauri desktop window, and served as the self-hosted dashboard — the only thing that changes between them is which capabilities the backend's `/runtime/bootstrap` response reports (e.g. desktop mode hides the login screen and the Users page; the underlying views are identical code).

```mermaid
flowchart LR
    subgraph FE["frontend/ — same build, two hosts"]
        WF["Workflows"]
        AQ["Approval Queue"]
        CN["Connections"]
        BV["Brand Voice"]
        SL["Self-Learning"]
        ST["Settings"]
        CO["Cost"]
        DG["Diagnostics"]
        US["Users (server only)"]
    end
    Tauri["Tauri window<br/>loopback + per-launch token"]
    API["FastAPI — self-hosted<br/>CORS-enabled for the dashboard's origin"]
    FE -->|desktop| Tauri
    FE -->|self-hosted| API
    style API fill:#0891b2,color:#fff
    style Tauri fill:#7c3aed,color:#fff
```

| View | Backend resource | What you can do |
|------|-------------------|-------------------|
| **Workflows** | `/workflows/*` | Manually trigger research, content, analytics, and engagement runs |
| **Approval Queue** | `/approvals/*` | See every pending gated action with full argument content shown (never a bare post ID) — approve, reject, or retry |
| **Connections** | `/credentials/*`, `/credentials/{id}/test` | Save API keys/tokens/connected-account IDs (encrypted at rest / OS keyring), then actually test them against the real provider — `connected` / `invalid` / `missing` / `unavailable`, not just "a value is stored" |
| **Brand Voice** | `/brand-voice/*` | Maintain titled brand-voice profiles that are also ingested into RAG |
| **Self-Learning** | `/learning/proposals/*`, `/learning/reflect` | Review reflection-job proposals (flagged clearly when a type can never auto-apply), trigger an on-demand reflection run |
| **Settings** | `/settings/{key}`, `/system/pause`, `/system/resume` | View/edit agent settings, and the kill switch — pause every approved external action system-wide |
| **Cost** | `/cost` | Today's LLM spend vs. the daily cap, as a progress bar |
| **Diagnostics** | `/diagnostics` | Live health of the database, runtime-state store, scheduler, vector store, credential store, and kill switch — plus, in desktop mode, one-click workspace backups |
| **Users** (admin, server only) | `/admin/users` | Invite teammates — each gets their own fully isolated workspace |

Every action carries a server-derived `decided_by` identity. Self-hosted mode uses the authenticated account; desktop mode uses the installation's stable local-owner identity. The same approval and proposal audit trails remain active in both modes.

Requires the backend running separately in self-hosted mode (see [Self-Hosted Development](#self-hosted-development)) with CORS allowing the dashboard's origin — `CORS_ALLOWED_ORIGINS` in `.env.example` already defaults to Vite's dev-server ports. The dashboard signs in through an HttpOnly server session and sends a CSRF token for mutations; no secret is compiled into the browser bundle. In desktop mode there's no session cookie at all — the Tauri shell authenticates the webview to its own sidecar directly. Full setup/build details: `frontend/README.md`.

---

## Testing & Validation Gates

```bash
# Gate 1 — foundation
pytest backend/tests/test_harness.py backend/tests/test_memory.py backend/tests/test_rag.py -v
python -m app.safety.audit

# Gate 2 — tools + safety
pytest backend/tests/test_tools.py backend/tests/test_safety.py -v

# Gate 3 — quality
pytest backend/evals -v --tb=short
python -m backend.evals.run_evals --compare-to-baseline

# Final gate
ruff check backend
mypy backend/app --ignore-missing-imports
pytest backend/tests backend/evals --cov=backend/app --cov=backend/evals --cov-fail-under=80
PYTHONPATH=backend python -m app.tools.registry --validate-all-schemas
PYTHONPATH=backend python -m app.safety.audit
cd frontend && npm run lint && npm run build

# Desktop shell (needs Rust + your OS's Tauri prerequisites — docs/desktop-development.md)
python scripts/check-version.py
bash scripts/build-sidecar.sh
cd src-tauri && cargo check
```

Current state: **592 tests passing**, ruff/mypy clean, frontend lint/build clean, tool-registry audit green, safety audit green. `.github/workflows/ci.yml` runs the backend and frontend gates above on every push/PR, plus a `desktop` job that compiles the Tauri shell natively on Ubuntu, Windows, and macOS runners.

---

## Project Status

Honest state, not aspirational: **version 0.1.0 is a working desktop development build and a working self-hosted deployment — not a signed, downloadable release yet.**

What's real and tested today:

- Every agent, safety gate, tool, eval, and the self-learning loop — all of it, in both runtime modes.
- Self-hosted mode: install via Docker Compose, works end-to-end, multi-tenant isolation between invited users verified (separate credentials, brand voice, approvals, cost caps — nothing leaks between accounts).
- Desktop mode on Linux: building it produces a real, working `.deb`/`.rpm`/`.AppImage`; smoke-tested — launches without any manually-installed Python/PostgreSQL/Redis, migrates its own SQLite database, authenticates its loopback API, and shuts down its sidecar cleanly with no orphan process (a real bug found and fixed this way: the frozen sidecar's own child process used to survive after the app closed).

What's not done yet:

- **Windows and macOS installers** haven't been built and smoke-tested on native machines — only compiled (`cargo check`) on GitHub-hosted CI runners so far. There's no guarantee a packaged build behaves identically there until that happens.
- **No code-signing, notarization, or update mechanism** exists yet — installers you build yourself are unsigned, and there's no auto-updater configured. That's a deliberate choice: shipping a real, secure signing/update pipeline is real infrastructure work, not something to fake.
- **No pre-built downloads** — every install path in this README involves building from source. A GitHub Releases page with real signed artifacts is the natural next milestone once the above is done.

See [`docs/desktop-implementation-status.md`](docs/desktop-implementation-status.md) for the detailed, continuously-updated list of what's verified vs. still open, and [`docs/desktop-migration-audit.md`](docs/desktop-migration-audit.md) for how the desktop shell was designed.

---

## Roadmap

**Done (this repo, right now):**
- [x] All 5 runtime agents, brand-voice/confidence-gated drafts
- [x] Human-approval flow blocking all 6 `requires_approval` tools, no bypass
- [x] Refusal-topic escalation across 5 categories
- [x] Multi-source Research Agent (6 sources, X optional)
- [x] Eval harness with regression gate
- [x] Self-learning loop with hard human-review lines
- [x] Production automation for research, engagement polling, retention, and approved scheduled publishing
- [x] Episodic analytics aggregation with real impressions, engagement, follower, and top-post metrics
- [x] FastAPI serving layer (`main.py`) — settings, approval queue, learning-proposal queue, cost, health, diagnostics, backup, all over the same tested infrastructure above
- [x] Self-learning loop running on an actual schedule (`learning/scheduler.py`, APScheduler, weekly by default, wired into the app's startup lifespan)
- [x] A real live LLM client (`model_router.route_and_call`) — Anthropic or OpenAI for primary/cheap tiers, Hermes/vLLM (OpenAI-compatible) for the worker tier, both via a forced structured tool-call so every existing agent's response-parsing contract is untouched
- [x] Dashboard UI for workflows, connections, brand voice, approval queue, self-learning queue, agent settings, cost, diagnostics, and user administration (`frontend/`, React + Vite)
- [x] Multi-tenant self-hosted mode — invite-only accounts, each with fully isolated credentials, brand voice, RAG index, approvals, and cost cap
- [x] Desktop runtime mode — Tauri shell, frozen Python sidecar, SQLite + OS keyring, no login, no PostgreSQL/Redis dependency
- [x] Live-tested provider connectivity checks (`POST /credentials/{id}/test`) and a Diagnostics view for every backing service
- [x] Production hardening: encrypted credential store (server) / OS keyring (desktop), Alembic-first startup with pre-migration backup, durable lock-protected FAISS snapshots, Docker Compose, CI (backend + frontend + native desktop compile matrix), and centralized Python tooling config

**In progress / explicitly not done:**
- [ ] Signed Windows and macOS installers, built and smoke-tested on native machines
- [ ] Code signing, notarization, and an auto-updater
- [ ] A GitHub Releases page with downloadable, pre-built artifacts

**Explicitly post-MVP (per the original spec):**
- [ ] Connection-relationship knowledge graph
- [ ] Analytics-driven auto-scheduling

**Known limitations carried into the live client:** `RouteAndCallResponse.tool_calls` is always `[]` — no runtime agent built in this codebase ever passes a non-`None` `tool_executor` to `run_step()` (agents call `tools.registry.execute_tool()` directly outside the harness loop), so harness-native tool execution/logging remains future work. Anthropic/OpenAI pricing in `.env.example` is placeholder defaults, not verified real per-token pricing — override before trusting the cost cap for anything real.

---

## How This Was Built

This system was built PRP-style: a detailed spec (`INITIAL.md`) generated a full implementation blueprint, executed in phases with validation gates between each:

```
Phase 1 (Foundation) → Phase 2 (5 runtime agents + safety) → Phase 3 (evals + self-learning)
  → Phase 4 (FastAPI serving layer + scheduled learning loop) → Phase 5 (live LLM client)
  → Phase 6 (multi-tenant self-hosted mode) → Phase 7 (desktop migration)
```

Each phase's validation gate had to pass before the next started. Every non-trivial design decision in this codebase — why X is optional, why deletion has no confidence bypass, why `system_prompt` changes can never auto-apply, why the desktop shell is Tauri instead of Electron — traces back to an explicit requirement in that phase's spec, not an implementation afterthought. The desktop migration specifically followed `desktopv.md`'s brief through a repository audit (`docs/desktop-migration-audit.md`) and a PRP (`docs/prp/desktop-production-migration.md`) before any runtime code changed.

---

## Contributing

Issues and pull requests are welcome. Before opening a PR:

1. Read [`CLAUDE.md`](CLAUDE.md) — the non-negotiable rules (approval gating, the LLM choke point, no silent context truncation, no capability without an eval) apply to human contributors exactly as much as to an AI agent working on this repo.
2. Run the [validation gates](#testing--validation-gates) relevant to what you changed before pushing.
3. If you touch anything under `backend/app/safety/`, `backend/app/tools/registry.py`, or approval-gating logic, run `python -m backend.app.safety.audit` explicitly and explain in the PR description why the change preserves every existing invariant.
4. New agent capabilities need a golden-set eval added under `backend/evals/` — a capability without one isn't considered done, per `CLAUDE.md`.

For desktop-shell changes specifically, see [`docs/desktop-development.md`](docs/desktop-development.md) for native prerequisites per OS, and [`docs/security-model.md`](docs/security-model.md) for the threat model any change there needs to preserve (loopback-only binding, per-launch token, no plaintext credential fallback).

---

## License

[MIT](LICENSE) — do whatever you want with this, including running your own fork against your own LinkedIn account and your own model provider. No attribution required, though it's appreciated.
