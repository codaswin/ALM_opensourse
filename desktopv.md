# MASTER EXECUTION PROMPT

## Convert AI LinkedIn Manager from Web App to a Production-Grade Desktop Application

You are working inside the existing repository:

`AI_LinkedIn_manager`

Repository:

`https://github.com/codaswin/AI_LinkedIn_manager.git`

Your task is **not** to casually wrap the existing React website inside Electron and call it a desktop application.

Your task is to perform a **careful architecture migration** of the existing AI LinkedIn Manager from its current VPS/web-first architecture into a **production-grade, open-source, installable desktop application**, while preserving the working agentic architecture, safety guarantees, approval system, tests, RAG behavior, workflows, and core functionality.

This application must eventually be usable by normal users on:

* Windows
* Linux
* macOS

A user should be able to clone/download/install the project and run their own independent AI LinkedIn Manager without depending on the original developer's VPS, database, API keys, domain, or infrastructure.

The existing web/VPS deployment capability may remain available as an **optional advanced deployment mode**, but the primary open-source user experience should become a desktop/local-first experience.

---

# 1. FIRST RULE — DO NOT START CODING IMMEDIATELY

Before making implementation changes:

1. Read the repository completely.
2. Understand the current architecture.
3. Inspect all important markdown/specification/documentation files.
4. Inspect the frontend.
5. Inspect the backend.
6. Inspect database and migration architecture.
7. Inspect Redis usage.
8. Inspect FAISS/RAG implementation.
9. Inspect scheduler architecture.
10. Inspect authentication and tenancy.
11. Inspect credentials/secrets handling.
12. Inspect Docker/VPS deployment.
13. Inspect testing/evals.
14. Inspect CI/CD.
15. Inspect all safety systems.
16. Inspect PRPs and historical design documentation.
17. Inspect `CLAUDE.md`.
18. Inspect `INITIAL.md`.
19. Inspect existing PRPs.
20. Inspect README/deployment documentation.
21. Inspect `.env` examples and production environment files.
22. Inspect the existing desktop-unfriendly assumptions throughout the codebase.

Do not blindly trust documentation.

The repository has evolved considerably, and some older markdown files may contain architecture decisions that are no longer accurate.

Always compare:

* documentation
* actual code
* tests
* migrations
* current frontend
* current production configuration

If documentation and code disagree, identify the discrepancy explicitly.

---

# 2. EXISTING PROJECT — PRESERVE THE CORE

The application is an AI-powered LinkedIn management system consisting of multiple specialized agents.

The current system includes five major runtime agents:

1. Content Strategist
2. Content Writer
3. Engagement Agent
4. Analytics & Reporting Agent
5. Research Agent

The Research Agent currently works across multiple sources such as:

* Hacker News
* Reddit
* GitHub
* Product Hunt
* RSS
* DuckDuckGo/web search
* optional X/Twitter support where configured

The system contains approximately 19 registered tools, with several high-risk LinkedIn actions requiring explicit human approval.

The desktop migration must **not destroy the agentic architecture**.

Do not simplify this into a chatbot.

Do not collapse the system into one generic LLM call.

Do not remove agent separation just because desktop packaging becomes easier.

---

# 3. NON-NEGOTIABLE SAFETY GUARANTEES

The existing safety-first architecture must remain intact.

Any modification must preserve these principles.

## 3.1 Human approval

Actions such as:

* publishing a LinkedIn post
* scheduling a LinkedIn post
* deleting a LinkedIn post
* replying to comments
* replying to DMs
* sending connection requests

must still require explicit human approval.

No desktop conversion is allowed to bypass this.

---

## 3.2 LLM choke point

The project's rule that LLM execution passes through the central harness must remain enforced.

Do not introduce random direct calls to:

* Anthropic
* OpenAI
* Hermes
* other model providers

from arbitrary agents, tools, UI handlers, routers, or desktop runtime code.

---

## 3.3 Kill switch

Preserve the system-wide kill switch.

The desktop UI should expose the kill-switch status clearly if appropriate.

A user must be able to immediately stop externally impactful actions.

---

## 3.4 Rate limits and cost limits

Preserve configurable limits including:

* LLM daily cost budget
* posts/day
* replies/day
* connection requests/day
* deletions/day
* likes/day

Desktop/local mode must not accidentally remove those protections.

---

## 3.5 Guardrails

Preserve all refusal-topic and sensitive-content guardrails.

Desktop packaging must never bypass engagement safety checks.

---

## 3.6 Evals

Do not ship new agent behavior without considering corresponding golden-set eval coverage.

Existing evaluation behavior must continue functioning.

---

# 4. PRIMARY MIGRATION GOAL

Convert the project into a desktop application that feels like a real software product.

The intended experience should roughly become:

```text
User downloads application
        ↓
Installs application
        ↓
Launches AI LinkedIn Manager
        ↓
Initial setup/onboarding
        ↓
Configures their own required credentials
        ↓
Application initializes user's local workspace
        ↓
User connects LinkedIn / AI providers
        ↓
Application becomes ready
        ↓
Agents + scheduler + RAG operate locally
```

The user should NOT need to manually:

* install PostgreSQL
* install Redis
* configure Nginx
* configure Caddy
* buy a domain
* rent a VPS
* configure TLS
* understand Docker Compose
* manually run backend commands
* manually launch frontend commands

for the standard desktop experience.

Those things may remain available for advanced/server deployment, but they should not be prerequisites for a desktop user.

---

# 5. DESKTOP TECHNOLOGY — DO NOT ASSUME ELECTRON

Do not automatically choose Electron.

Perform a technical evaluation of at least:

* Tauri
* Electron
* any other serious, production-ready alternative that fits this repository

Evaluate them based on:

* Windows support
* Linux support
* macOS support
* React/Vite compatibility
* Python/FastAPI backend integration
* subprocess management
* security
* application size
* memory usage
* packaging complexity
* automatic updates
* signing/notarization
* filesystem access
* OS keychain integration
* developer experience
* open-source maintainability
* CI/release complexity

Then choose the best architecture.

Document the decision using an ADR-style document.

Example:

`docs/adr/desktop-runtime.md`

The decision must be justified.

Do not choose technology only because it is popular.

---

# 6. PRESERVE THE EXISTING REACT FRONTEND WHERE PRACTICAL

The current frontend is React + Vite + TypeScript.

Do not rebuild it unnecessarily.

Prefer adapting and reusing the existing frontend.

The desktop migration should primarily redesign:

* runtime environment
* backend lifecycle
* storage
* authentication assumptions
* onboarding
* credentials
* local services
* error recovery
* packaging
* updates
* desktop integration

rather than replacing a functioning frontend.

---

# 7. REMOVE NORMAL LOGIN REQUIREMENT FROM LOCAL DESKTOP MODE

The existing web application contains authentication because it was built for server/multi-user deployment.

For a standard local desktop installation:

**Do not require a login page every time the owner opens their own software.**

Desktop-local mode should represent a trusted local workspace.

Design a clean local-owner model.

Possible experience:

```text
First launch
   ↓
Create local workspace
   ↓
Optional local protection
   ↓
Normal future launches open directly
```

Do not remove authentication code blindly.

The application may still require authentication in:

* VPS mode
* hosted mode
* shared server mode
* multi-user/team deployment

Therefore implement an architecture that cleanly distinguishes:

```text
Desktop Local Mode
vs
Server / Multi-user Mode
```

Avoid scattering random:

```python
if desktop:
```

checks across the whole codebase.

Use a proper runtime/deployment mode abstraction.

---

# 8. MULTI-TENANCY MUST BE RE-EVALUATED — NOT RANDOMLY DELETED

The current project has multi-tenant isolation.

This is important for hosted deployments.

However, one desktop installation will generally represent one owner/user.

Perform a careful architecture analysis.

The desired model is approximately:

## Desktop mode

```text
Installation A
 └── User A
      ├── credentials
      ├── memory
      ├── RAG
      ├── settings
      ├── approvals
      ├── scheduler
      └── analytics

Installation B
 └── User B
      ├── credentials
      ├── memory
      ├── RAG
      ├── settings
      ├── approvals
      ├── scheduler
      └── analytics
```

There must NEVER be one globally shared RAG/database/credential environment across unrelated desktop users.

Each installation must initialize its own independent workspace automatically.

However, do not destroy multi-tenant capability required by VPS/hosted mode unless there is a strong architectural reason.

Prefer a shared core that supports:

```text
Local single-workspace deployment
Hosted multi-workspace deployment
```

without duplicating the entire application.

---

# 9. EACH INSTALLATION MUST GET ITS OWN RAG

This is mandatory.

When User A installs the software:

```text
User A application
   ↓
User A local semantic index
```

When User B installs the software:

```text
User B application
   ↓
User B separate semantic index
```

No shared central FAISS index.

No developer-controlled RAG.

No shared user embeddings.

No cross-installation contamination.

The RAG lifecycle must support:

* initialization
* ingestion
* updates
* deduplication
* persistence
* backup
* restore
* reindexing
* deletion
* migration between application versions

Store RAG data in an OS-appropriate application data directory.

Examples conceptually:

Windows:

```text
%APPDATA%/AI-LinkedIn-Manager/
```

Linux:

```text
~/.local/share/ai-linkedin-manager/
```

macOS:

```text
~/Library/Application Support/AI LinkedIn Manager/
```

Do not hardcode these exact paths if the chosen desktop framework has better OS-native path APIs.

---

# 10. DATABASE ARCHITECTURE MUST BE RE-EVALUATED

The existing architecture uses PostgreSQL.

That is suitable for VPS deployment.

It may be unnecessarily heavy for a local desktop installation.

Evaluate options including:

### Option A

Keep local PostgreSQL and bundle/manage it.

### Option B

Use SQLite for desktop mode and PostgreSQL for server mode.

### Option C

Use an embedded database suitable for desktop deployments.

### Option D

Use another architecture if technically superior.

Do not make the choice based purely on convenience.

Evaluate:

* migrations
* SQLAlchemy compatibility
* transactions
* concurrency
* scheduler
* approvals
* analytics
* episodic memory
* reliability
* backup
* data corruption risk
* installer size
* maintenance
* cross-platform packaging

Prefer minimal architectural divergence.

If SQLite can safely support desktop mode, investigate using SQLAlchemy abstractions so the same models can support:

```text
SQLite → Desktop
Postgres → Server
```

Avoid creating two entirely separate backend codebases.

---

# 11. REDIS MUST ALSO BE RE-EVALUATED

The current application uses Redis for:

* working memory
* locking
* scheduler ownership
* runtime state
* possibly throttling/caching

A normal desktop user should not have to install Redis manually.

Analyze whether desktop mode should use:

* embedded/local replacement
* SQLite-backed state
* in-process state + persistence
* lightweight embedded KV store
* bundled Redis
* another robust alternative

Hosted/server mode can continue using Redis where appropriate.

The important thing is preserving behavior:

* locks
* working memory
* rate limiting
* scheduler safety
* idempotency
* concurrency protection

Do not simply replace Redis with an unprotected Python dictionary.

---

# 12. FASTAPI BACKEND

The existing FastAPI backend can remain if it is still architecturally sensible.

For desktop mode, evaluate:

```text
Desktop shell
      ↓
starts backend process automatically
      ↓
backend binds only to localhost
      ↓
frontend communicates locally
```

Possible architecture:

```text
Desktop Runtime
 ├── React UI
 ├── Local FastAPI process
 ├── Local database
 ├── Local semantic store
 ├── Scheduler
 └── Secure credential store
```

If this architecture is selected:

* automatically select/manage an available local port
* avoid exposing backend externally
* bind to `127.0.0.1`
* protect desktop-local IPC/API appropriately
* start backend automatically
* detect backend crashes
* restart safely where appropriate
* shut backend down when application closes where appropriate
* prevent orphan processes
* preserve logging
* provide diagnostics

Do not make the user open a terminal.

---

# 13. DESKTOP ONBOARDING

Replace the web-login-first experience with an onboarding flow.

Suggested flow:

```text
Welcome
   ↓
Local workspace creation
   ↓
AI Provider
   ↓
LinkedIn / Composio setup
   ↓
Optional external services
   ↓
Brand voice
   ↓
Research interests
   ↓
Safety / approval explanation
   ↓
Connection test
   ↓
Ready
```

Do not overwhelm users by asking for every possible optional API key at first launch.

Separate credentials into:

### Required to perform core action

### Optional

### Advanced

### Provider-specific

The UI should clearly explain why a credential is required.

---

# 14. INTELLIGENT MISSING-CREDENTIAL RECOVERY

This is a major UX requirement.

Currently, an action may produce an error like:

```text
COMPOSIO_API_KEY missing
```

or:

```text
Provider credential not configured
```

This is unacceptable as the primary user experience.

Instead implement **actionable error recovery**.

Example:

User clicks:

```text
Generate Post
```

If Anthropic/OpenAI configuration is missing:

```text
System detects missing AI provider
        ↓
User sees clear message
        ↓
Navigate/open Connections
        ↓
AI provider section automatically expands
        ↓
Missing field highlighted
        ↓
Explanation displayed
        ↓
User enters credential
        ↓
Credential tested
        ↓
Saved securely
        ↓
User returns to previous workflow
        ↓
Original action can be retried
```

Another example:

User attempts:

```text
Approve & Publish LinkedIn Post
```

Composio is missing:

```text
Publishing requires LinkedIn integration.
Your Composio connection has not been configured.
```

Then automatically:

```text
Connections
   ↓
Composio section
   ↓
Highlight required credential/connection action
```

The user should not have to search through settings manually.

---

# 15. BUILD A STRUCTURED DEPENDENCY-ERROR SYSTEM

Do not implement this UX using string matching such as:

```typescript
if (error.includes("COMPOSIO"))
```

Create structured backend errors.

For example conceptually:

```json
{
  "error_code": "MISSING_INTEGRATION",
  "provider": "composio",
  "required_for": "publish_post",
  "recoverable": true,
  "recovery_target": {
    "view": "connections",
    "section": "composio"
  }
}
```

Or another well-designed schema.

Possible classes:

```text
MissingCredentialError
InvalidCredentialError
ExpiredCredentialError
MissingIntegrationError
ProviderUnavailableError
ConfigurationRequiredError
```

The frontend should interpret these errors and provide recovery UI.

---

# 16. INVALID AND EXPIRED CREDENTIALS

Handle more than "missing."

Support:

```text
missing
invalid
expired
revoked
permission insufficient
provider unavailable
rate limited
```

Example:

```text
LinkedIn connection expired.

Reconnect LinkedIn to continue.
```

Click:

```text
Reconnect
```

takes the user directly to the correct Connections flow.

---

# 17. RETURN-TO-WORKFLOW BEHAVIOR

After fixing configuration, the application should remember where the user came from.

Example:

```text
Research → Generate Content → Missing Anthropic Key
```

After fixing Anthropic:

```text
Connections → save → test → Back
```

should return to:

```text
Generate Content
```

with the previous context preserved where safe.

Consider a recovery context such as:

```text
returnRoute
workflow
action
payload reference
```

Do not preserve secrets in route parameters or insecure frontend storage.

---

# 18. CREDENTIAL SECURITY

Desktop credential security is mandatory.

Do not store production credentials as plain text inside:

* source files
* frontend localStorage
* committed `.env`
* JSON configuration files
* logs
* crash reports

Investigate OS-native secure storage.

Examples:

* Windows Credential Manager
* macOS Keychain
* Linux Secret Service / libsecret

If the desktop framework provides a trusted cross-platform secure-storage plugin, evaluate it.

The backend should retrieve secrets through an abstraction.

Example conceptually:

```python
CredentialStore
├── DesktopSecureCredentialStore
└── ServerEncryptedDatabaseCredentialStore
```

Do not tightly couple agent code to desktop-specific secret APIs.

---

# 19. API KEYS BELONG TO THE USER

This project will be open source.

Every installation must use **the user's own credentials**.

Examples may include:

* Anthropic
* OpenAI
* Composio
* GitHub
* Product Hunt
* X/Twitter
* other optional sources

Never ship the developer's API keys.

Never route open-source user traffic through the developer's private credentials.

Never create hidden telemetry requiring the developer's infrastructure.

---

# 20. CONNECTION TESTING

Whenever a user saves an API key or provider configuration:

1. Validate format where practical.
2. Save securely.
3. Test connectivity.
4. Return provider-specific status.
5. Reset any cached SDK client.
6. Update UI immediately.

This repository previously had a stale cached SDK-client problem after credentials changed.

Do not reintroduce it.

Credential save/delete/update must invalidate any related cached provider client.

---

# 21. CONNECTIONS PAGE REDESIGN

Redesign Connections into a desktop-friendly configuration center.

Possible structure:

```text
Connections

AI Providers
 ├── Anthropic       Connected
 ├── OpenAI          Not configured
 └── Hermes          Optional

LinkedIn
 └── Composio        Connected

Research
 ├── GitHub          Connected
 ├── Product Hunt    Optional
 ├── X               Optional
 └── RSS             No credentials required

Search
 └── DuckDuckGo      Ready
```

Each integration should communicate:

* configured/not configured
* connected/disconnected
* required/optional
* last test
* reconnect
* edit
* delete
* what features depend on it

Avoid showing raw developer terminology unnecessarily.

---

# 22. PROVIDER CAPABILITY MAPPING

Create a central capability/dependency mapping.

Example conceptually:

```text
generate_content
 └── requires one configured LLM provider

publish_linkedin
 └── requires LinkedIn/Composio

github_research
 └── GitHub credential optional depending on limits

producthunt_research
 └── Product Hunt token

x_research
 └── X API credentials
```

Then the UI/backend can determine requirements programmatically.

Do not duplicate credential requirement logic in every view.

---

# 23. SELF-HOSTED / VPS MODE MUST REMAIN POSSIBLE

A technical user should still be able to deploy the application using something like:

```text
Docker
Docker Compose
VPS
domain
reverse proxy
PostgreSQL
Redis
```

if desired.

Therefore target:

```text
One Core Application
        ↓
 ┌──────────────┬───────────────┐
 │ Desktop Mode │ Server Mode   │
 └──────────────┴───────────────┘
```

Not:

```text
Desktop repository
Server repository
```

unless absolutely unavoidable.

---

# 24. OPEN-SOURCE INSTALLATION EXPERIENCE

The final repository should make the difference clear.

Example README:

```text
## Install

### Option 1 — Desktop Application
Recommended for individuals.

Windows
macOS
Linux

### Option 2 — Self-host
Recommended for teams/servers.

Docker Compose
```

A beginner should know which one to choose.

---

# 25. BUILD / RELEASE SYSTEM

Create a proper desktop release pipeline.

Investigate GitHub Actions for producing installers.

Possible outputs depending on chosen framework:

Windows:

```text
.exe
.msi
```

macOS:

```text
.dmg
.app
```

Linux:

```text
.AppImage
.deb
.rpm
```

Do not promise unsupported formats unnecessarily.

Build only formats supported robustly by the selected runtime.

---

# 26. APPLICATION VERSIONING

Implement a clear application version source.

Avoid maintaining unrelated versions manually in:

* Python
* package.json
* desktop runtime
* installer

Prefer one authoritative version or an automated synchronization mechanism.

---

# 27. UPDATES

Evaluate automatic application updates.

Requirements:

* cryptographically trusted releases
* user consent
* safe update flow
* migration handling
* rollback/failure behavior
* no silent downloading/execution from arbitrary URLs

If auto-update is not appropriate initially, document a safe manual-update experience.

---

# 28. DATA MIGRATIONS

A desktop app will evolve.

A user installing v1 must be able to upgrade to v2 without losing:

* posts
* analytics
* approvals
* memory
* credentials
* brand voice
* research data
* RAG state

Create a migration strategy.

Database schema changes must remain migration-controlled.

RAG format/version changes must also have a migration/rebuild strategy.

---

# 29. BACKUP & RESTORE

Desktop users should eventually be able to back up their workspace.

Design a safe abstraction for:

```text
Export Backup
Restore Backup
```

Consider:

* SQL/database data
* FAISS/vector index
* configuration
* brand voice
* research data

Secrets require special treatment.

Do not casually export API keys into an unencrypted ZIP.

If backup implementation is beyond the first migration milestone, design/document it and mark it clearly.

---

# 30. LOGGING

Desktop logs must be useful but safe.

Provide an easy action such as:

```text
Open Logs Folder
```

Never log:

* API keys
* access tokens
* passwords
* authorization headers
* encryption keys

Consider automatic redaction.

---

# 31. DIAGNOSTICS

Add a diagnostic view if practical:

```text
System Status

Backend            Running
Database           Healthy
Scheduler          Running
Vector Store       Ready
Anthropic          Connected
Composio           Connected
LinkedIn           Connected
Kill Switch        Disabled
```

This will significantly simplify open-source support.

---

# 32. DESKTOP PROCESS LIFECYCLE

If backend/subprocess architecture is chosen:

Handle:

* app startup
* backend startup
* health check
* failed startup
* backend restart
* graceful shutdown
* forced shutdown
* orphan-process cleanup
* OS sleep/resume
* application restart

Do not leave Python servers running after the desktop application exits unintentionally.

---

# 33. SCHEDULER BEHAVIOR

The current system uses scheduled background tasks.

Desktop introduces special questions:

What happens when:

* app is minimized?
* window closes?
* computer sleeps?
* application exits?
* OS restarts?

Decide and document this.

Possible behavior:

```text
Close window → minimize to tray
Quit → actually stop scheduler
```

or another architecture.

Do not silently assume web-server semantics.

---

# 34. SYSTEM TRAY

Evaluate whether the application benefits from a tray/background mode.

Potential actions:

```text
Open AI LinkedIn Manager
Pause Automations
Resume Automations
Kill Switch
Quit
```

Only implement if it improves UX and remains secure.

---

# 35. NOTIFICATIONS

Evaluate OS-native notifications for:

* approval required
* connection expired
* workflow completed
* provider error
* scheduled content ready

Do not expose private message/post content in notifications by default.

---

# 36. DEEP LINKING

If helpful, consider internal deep links like:

```text
ai-linkedin-manager://connections/composio
```

This could support notifications and configuration recovery.

Implement only if the chosen framework supports it safely.

---

# 37. NO SECRET FRONTEND AUTHORITY

The desktop frontend must not become trusted merely because it is local.

Sensitive operations should remain backend-enforced.

Do not move security-critical approval enforcement entirely to React.

The backend must continue validating:

* approvals
* rate limits
* kill switch
* authorization/runtime mode
* credential requirements

The UI is a user experience layer, not the final security boundary.

---

# 38. LOCAL API SECURITY

If FastAPI runs locally:

Do not assume:

```text
localhost = automatically secure
```

Evaluate threats from:

* malicious browser tabs
* local malware
* cross-origin requests
* predictable ports
* CSRF-like localhost attacks

Use appropriate controls such as:

* loopback-only binding
* randomly generated session token
* strict CORS/origin policy
* desktop-issued local auth token
* secure IPC where supported

Choose the cleanest solution based on the desktop framework.

---

# 39. WEB AUTH CODE

Do not immediately delete existing authentication.

Refactor it so:

```text
Server Mode
    → login/session/roles/multi-user

Desktop Mode
    → local-owner session/bootstrap
```

Keep logic clean.

If pieces become genuinely obsolete, remove them only after proving they are unused.

---

# 40. ADMIN / USER MANAGEMENT

The server version currently supports invited users/admin-oriented multi-tenancy.

Desktop single-user mode likely does not need:

```text
Users
Invite User
Admin account management
```

Hide or disable those views in desktop mode.

Do not necessarily delete server functionality.

Runtime capabilities should determine UI availability.

---

# 41. SETTINGS

Create a clear desktop settings model.

Potential sections:

```text
General
Connections
AI Models
Automation
Safety
Rate Limits
Costs
Data & Storage
Backups
Advanced
About
```

Avoid mixing development configuration with normal user settings.

---

# 42. MODEL CONFIGURATION

Do not hardcode model names unnecessarily.

Continue using the existing model router philosophy.

UI may allow supported model configuration where appropriate.

Preserve:

```text
primary model
cheap model
worker/local model
```

if current architecture supports them.

---

# 43. HERMES / LOCAL INFERENCE

The application has optional self-hosted Hermes support.

Do not make Hermes mandatory.

Desktop migration should preserve the possibility of:

```text
Cloud LLM
or
Local/self-hosted Hermes
```

If direct local Hermes bundling is too heavy, keep it as an advanced integration.

---

# 44. RESEARCH PIPELINE

Preserve the current multi-source research system.

Do not regress it to X/Twitter-only architecture because an old PRP says so.

Sources should fail independently.

One unavailable provider must not destroy the entire research run.

Preserve concurrent fetching where appropriate.

Preserve ranking/deduplication.

---

# 45. HISTORICAL BUGS MUST INFORM THE MIGRATION

Study repository history/docs/tests for previous bugs.

Especially avoid reintroducing classes of bugs involving:

* overly broad `.gitignore`
* local `.env` leaking into tests
* CORS middleware ordering
* wrong schedule-vs-publish behavior
* controlled-input UX bugs
* topic drift
* cached provider credentials
* rate-limit production configuration
* reverse-proxy routing
* tenant leakage
* CSRF race conditions

When modifying related areas, add/retain regression coverage.

---

# 46. DOCUMENTATION AUDIT

Audit every major `.md` file.

Classify it as:

```text
KEEP
UPDATE
REWRITE
ARCHIVE
DELETE
```

Do not retain contradictory documentation simply because it already exists.

Examples likely requiring review:

```text
README.md
CLAUDE.md
INITIAL.md
PRPs/*
deploy/README.md
architecture docs
setup docs
environment docs
security docs
```

For each modified document, preserve useful historical reasoning but remove false current-state claims.

---

# 47. INITIAL.MD

`INITIAL.md` was part of the original PRP workflow.

It may no longer represent the current product accurately.

Do not blindly append desktop requirements to stale architecture.

Evaluate whether to:

### Rewrite `INITIAL.md`

or

### Archive old version and create something like:

```text
INITIAL.desktop.md
```

or

```text
docs/specs/desktop-product-spec.md
```

Choose the approach that keeps future AI coding assistants from being confused.

The active source-of-truth must be obvious.

---

# 48. CLAUDE.MD

Review `CLAUDE.md`.

Preserve all still-valid non-negotiable rules.

Update it with desktop architecture constraints such as:

* runtime modes
* secure storage
* local data directories
* no hardcoded ports
* desktop/backend lifecycle
* no plaintext desktop secrets
* cross-platform compatibility
* structured recoverable errors
* server functionality preservation

Do not weaken existing safety rules.

---

# 49. PRPs

The project uses PRP-style development.

Create a new implementation PRP for this migration.

Suggested filename:

```text
PRPs/desktop-application-migration.md
```

The PRP should contain:

* objective
* existing architecture
* target architecture
* technology decision
* affected modules
* data model changes
* migration strategy
* auth/tenancy changes
* credential architecture
* RAG changes
* Redis/database changes
* desktop lifecycle
* UX changes
* security threats
* tests
* evals
* documentation changes
* packaging
* release strategy
* rollback strategy
* validation commands
* completion criteria

Make it detailed enough that another coding agent could execute it without inventing architecture.

---

# 50. ARCHITECTURE DOCUMENT

Create/update a current architecture document.

Suggested:

```text
docs/architecture.md
```

It should clearly show:

```text
Core Agents
Harness
Tools
Memory
RAG
Learning
Safety
Provider clients
Storage adapters
Runtime mode
Desktop shell
Server deployment
```

Include diagrams using Mermaid where useful.

---

# 51. RUNTIME MODE ABSTRACTION

Create a clean abstraction conceptually like:

```text
RuntimeMode.DESKTOP
RuntimeMode.SERVER
```

or a better architecture.

Runtime mode should control things such as:

```text
auth strategy
storage strategy
credential strategy
scheduler ownership
frontend capabilities
server networking
multi-user UI
```

Avoid hidden behavior based purely on environment variables scattered throughout the repository.

Centralize runtime configuration.

---

# 52. STORAGE ABSTRACTIONS

Where necessary, introduce interfaces/adapters.

For example conceptually:

```text
DatabaseBackend
CredentialStore
WorkingMemoryStore
SemanticStore
RuntimeIdentityProvider
```

Do not over-engineer.

Only introduce abstractions where desktop/server divergence actually exists.

---

# 53. LOCAL USER IDENTITY

Desktop mode still needs a stable internal identity because existing tables/state may reference `user_id`.

Instead of ripping out user scoping, consider creating a deterministic local workspace owner.

Example:

```text
desktop-local-owner
```

or a generated installation-scoped UUID.

Evaluate what works best with:

* migrations
* RAG namespaces
* existing models
* scheduler
* credentials
* approvals

This may allow the existing tenant-aware architecture to remain mostly intact while desktop exposes only one workspace.

---

# 54. FIRST-RUN WORKSPACE

On first launch:

1. Determine app data path.
2. Create required directories.
3. Initialize local database.
4. Run migrations.
5. Create local workspace identity.
6. Initialize semantic store.
7. Initialize settings.
8. Initialize encryption/credential backend.
9. Start scheduler.
10. Start backend.
11. Perform health checks.
12. Open onboarding.

This must be idempotent.

Restarting the application must not create another user/workspace each time.

---

# 55. DIRECTORY LAYOUT

Design a clean application-data layout.

Conceptually:

```text
AI LinkedIn Manager/
├── database/
├── rag/
├── logs/
├── backups/
├── cache/
├── runtime/
└── config/
```

Secrets should not be stored as plain files here unless securely encrypted and justified.

---

# 56. DEVELOPMENT MODE

Keep developer experience easy.

A contributor should still be able to run:

```text
frontend
backend
tests
```

without always packaging a desktop installer.

Provide commands such as conceptually:

```text
npm run desktop:dev
npm run desktop:build
```

or framework equivalents.

---

# 57. DOCKER

Do not remove Docker support if it remains useful.

Docker should become primarily:

```text
Server/self-host mode
```

The desktop installer should not simply run Docker under the hood unless there is an overwhelming architectural reason.

Requiring Docker Desktop would make the product far less accessible.

---

# 58. CI

Update CI to validate:

* Python tests
* frontend tests
* safety audit
* desktop compilation
* packaging configuration
* type checking
* linting
* migrations
* cross-platform-sensitive logic

Avoid making every pull request produce full signed installers if too expensive.

Separate:

```text
CI validation
Release builds
```

where appropriate.

---

# 59. TESTING

Do not reduce existing coverage.

Add tests for desktop-specific behavior.

Required categories should include:

### Runtime mode

```text
desktop mode
server mode
```

### Credential recovery

```text
missing credential
invalid credential
expired credential
reconnect
cache invalidation
```

### First launch

```text
workspace creation
migration
restart idempotency
```

### Local identity

```text
same installation retains same identity
different installations do not share state
```

### RAG isolation

```text
Workspace A data unavailable to Workspace B
```

### Storage paths

Cross-platform path resolution should be tested where practical.

### Backend lifecycle

```text
startup
health failure
shutdown
restart
```

### Safety

Desktop mode must not bypass approval-gated tools.

---

# 60. SECURITY REVIEW

Before considering migration complete, perform a desktop threat-model review.

Consider:

* malicious local website attacking localhost API
* stolen desktop credentials
* log leakage
* token leakage
* insecure updates
* malicious plugins/packages
* permissions
* writable executable directories
* path traversal
* unsafe subprocess spawning
* shell injection
* backend port exposure
* cross-user leakage on shared computers
* backup leakage

Document mitigations.

---

# 61. OPEN SOURCE SECURITY

Ensure `.gitignore` correctly excludes actual secrets without excluding legitimate source files.

Do not return to broad patterns such as:

```text
*credentials*
*secrets*
```

that could hide real modules.

Use narrow patterns.

---

# 62. ERROR UX

Normal users should not see Python stack traces.

Create layers:

```text
User-facing message
Diagnostic code
Developer log
```

Example:

```text
We couldn't connect to Anthropic.

Check your Anthropic API key in Connections.

Error code: AI_PROVIDER_AUTH_FAILED
```

Developer logs may contain technical details, but never raw secret values.

---

# 63. ERROR BOUNDARIES

Add frontend error boundaries where appropriate.

One failing view should not crash the entire desktop application.

Backend failures should produce actionable UI.

---

# 64. OFFLINE BEHAVIOR

Define what works without internet.

Potentially available offline:

* viewing old posts
* analytics history
* saved drafts
* settings
* local data
* local inference if configured

Unavailable:

* LinkedIn actions
* internet research
* cloud LLM calls

Display meaningful status.

---

# 65. NETWORK STATUS

Consider displaying:

```text
Online
Offline
LinkedIn unavailable
Provider unavailable
```

without spamming users.

---

# 66. DATA OWNERSHIP

The open-source desktop edition must reinforce:

```text
Your credentials
Your data
Your RAG
Your computer
```

No hidden central account requirement.

No developer-owned cloud dependency should be necessary unless explicitly documented as optional.

---

# 67. TELEMETRY

Do not introduce analytics/telemetry without explicit consideration.

If telemetry is ever added:

* opt-in or transparent
* privacy-respecting
* no content
* no credentials
* no LinkedIn private data

For this migration, default to no hidden telemetry.

---

# 68. LICENSE / OPEN-SOURCE READINESS

Review repository licensing.

Ensure the selected desktop framework, libraries, secure-storage plugins, installer tooling, icons, and embedded components are license-compatible.

Document third-party notices if required.

---

# 69. BRANDING

Create a proper desktop application identity.

Examples:

```text
AI LinkedIn Manager
```

Need:

* app name
* package identifier
* icon strategy
* executable name
* window title
* installer metadata

Do not invent a commercial branding change unless repository context already defines one.

---

# 70. DO NOT BREAK SERVER DEPLOYMENT

Every major refactor must verify that server mode still works.

At minimum maintain tests/configuration verifying:

```text
FastAPI
PostgreSQL
Redis
multi-user auth
Docker
scheduler
multi-tenancy
```

where applicable.

---

# 71. MIGRATION PHASES

Do not implement everything in one giant uncontrolled patch.

Use gated phases.

Recommended structure:

---

## PHASE 0 — Repository Audit

Deliver:

```text
docs/desktop-migration-audit.md
```

Include:

* current architecture
* desktop blockers
* stale documentation
* risky assumptions
* dependency inventory
* affected modules
* recommended target architecture

No major code migration before this passes review.

---

## PHASE 1 — Architecture & Specification

Create/update:

```text
PRPs/desktop-application-migration.md
docs/architecture.md
desktop ADR
security model
runtime mode design
storage design
```

Define validation criteria.

---

## PHASE 2 — Runtime Abstractions

Implement:

* runtime mode
* local workspace identity
* storage interfaces where needed
* configuration cleanup
* structured error system

Keep existing server behavior passing.

---

## PHASE 3 — Desktop Storage

Implement:

* desktop database
* local memory
* local RAG
* secure credential storage
* app-data paths
* migrations
* first-run initialization

Validate isolation.

---

## PHASE 4 — Desktop Runtime

Implement selected desktop framework.

Add:

* frontend hosting
* backend process lifecycle
* local API security
* app window
* graceful shutdown
* logs
* diagnostics

---

## PHASE 5 — Desktop UX

Implement:

* remove desktop login requirement
* onboarding
* Connections redesign
* missing credential recovery
* return-to-workflow flow
* desktop settings
* server-only UI hiding

---

## PHASE 6 — Automation / Background Behavior

Implement:

* scheduler desktop lifecycle
* tray behavior if approved
* sleep/resume handling
* notifications if approved

---

## PHASE 7 — Packaging

Implement:

* Windows packaging
* Linux packaging
* macOS packaging
* release CI
* installer metadata
* application icons
* versioning

---

## PHASE 8 — Documentation

Rewrite all stale docs.

Update:

```text
README
CLAUDE.md
setup guides
deployment docs
contributor docs
```

Clearly distinguish Desktop vs Self-host.

---

## PHASE 9 — Final Validation

Run:

* complete backend tests
* frontend tests
* safety audit
* evals
* desktop build
* server build
* migration test
* clean-install test
* upgrade test
* credential test
* RAG isolation test

Do not call migration complete until validations pass.

---

# 72. DOCUMENTATION REWRITE AUTHORITY

You are explicitly authorized to:

* rewrite
* replace
* reorganize
* archive
* rename
* remove

outdated markdown/specification files when doing so improves the project's source-of-truth clarity.

However:

Do not delete useful history without reason.

For materially historical documents, prefer something like:

```text
docs/archive/
```

when future reference is valuable.

At the end, there must not be multiple active documents giving contradictory architecture instructions to future Claude/Codex agents.

---

# 73. CODE REFACTOR AUTHORITY

You are authorized to refactor existing code where necessary for the desktop architecture.

However:

Do not rewrite working subsystems simply because you would personally design them differently.

Preserve battle-tested logic whenever reasonable.

Prefer incremental refactors backed by tests.

---

# 74. CLEANUP

Remove:

* unused imports
* dead desktop-incompatible code where genuinely obsolete
* duplicated configuration
* obsolete environment variables
* stale comments
* outdated docs
* accidental debug code

Do not perform unrelated beautification/refactoring that massively increases migration risk.

---

# 75. QUALITY STANDARD

Treat this as a serious open-source software product.

The final system should be:

* understandable
* secure
* cross-platform
* maintainable
* testable
* documented
* deterministic where possible
* migration-safe
* beginner-friendly
* developer-friendly

Avoid:

* hacks
* hidden assumptions
* massive god files
* duplicated logic
* unexplained environment variables
* magical startup scripts
* swallowing exceptions
* security by obscurity

---

# 76. IMPORTANT — ASK CODE, NOT THE USER, WHEN POSSIBLE

If you are unsure how the current application works:

Inspect the repository.

Do not ask the user questions that can be answered by reading:

* code
* tests
* documentation
* Git history
* configuration

Only surface a user decision when it represents a genuine product choice that cannot reasonably be inferred.

When a safe and sensible default exists, choose it and document it rather than stopping execution unnecessarily.

---

# 77. VALIDATE EVERY PHASE

After each implementation phase:

1. Run relevant tests.
2. Run type checking.
3. Run linting where configured.
4. Run safety audit.
5. Check regressions.
6. Fix failures before continuing.
7. Commit logical changes separately where appropriate.

Do not accumulate 50 broken files and attempt validation only at the end.

---

# 78. PRESERVE GIT HISTORY

Do not wipe or recreate the repository.

Do not delete `.git`.

Do not squash everything automatically.

Make changes in understandable units.

---

# 79. DO NOT TOUCH USER SECRETS

If real API keys exist in the developer machine/repository environment:

Do not print them.

Do not move them into documentation.

Do not commit them.

Do not include them in fixtures.

Use mocked/test values.

---

# 80. DEFINITION OF DONE

The migration is considered successful when a completely new user can:

```text
1. Download/install AI LinkedIn Manager.
2. Open the application.
3. Complete onboarding.
4. Enter their own credentials.
5. Have credentials stored securely.
6. Have an isolated local database.
7. Have an isolated local RAG.
8. Configure their brand voice.
9. Run research.
10. Generate content.
11. Receive approval requests.
12. Approve a LinkedIn action.
13. Execute the action through their own integration.
14. Receive useful guidance if configuration is missing.
15. Close and reopen the app without losing data.
```

without:

```text
renting a VPS
buying a domain
installing PostgreSQL manually
installing Redis manually
editing source code
opening terminals
manually starting backend services
```

Additionally, an advanced user must still be able to self-host the server version.

---

# 81. EXPECTED FINAL REPOSITORY EXPERIENCE

The repository should eventually communicate something like:

```text
AI LinkedIn Manager
Safety-first AI agents for managing your LinkedIn presence.

Choose how you want to run it:

Desktop
--------
Best for individuals.
Install and run locally on Windows, Linux, or macOS.

Self-hosted
-----------
Best for servers, agencies, or multi-user teams.
Deploy using Docker Compose on your own VPS.
```

---

# 82. REQUIRED OUTPUT BEFORE MAJOR IMPLEMENTATION

Before implementing the migration, produce an audit summary containing:

## Current Architecture

Explain how the application works today.

## Desktop Blockers

List everything preventing a clean desktop experience.

## Documentation Conflicts

Identify stale/contradictory MD files.

## Recommended Desktop Stack

Compare desktop runtime choices and recommend one.

## Data Strategy

Explain:

* database
* Redis replacement/retention
* FAISS
* app-data paths
* credentials

## Authentication Strategy

Explain desktop vs server identity.

## Backend Strategy

Explain how FastAPI will run in desktop mode.

## Security Strategy

Explain localhost API and secret security.

## Migration Strategy

List implementation phases.

## Files to Modify

List important files/directories.

## Files to Rewrite

List documentation/configuration files requiring replacement.

## Files to Archive/Delete

Only where justified.

## Risks

List migration risks and mitigations.

Only after this audit is internally coherent should major implementation proceed.

---

# 83. WHEN EXECUTING WITH CODEX OR CLAUDE CODE

This specification is intended to work with either Codex or Claude Code.

Whichever coding agent executes it:

* read repository instructions first
* respect existing `CLAUDE.md`
* inspect before editing
* use tests continuously
* do not invent architecture without validating current code
* keep documentation synchronized with implementation
* preserve safety boundaries
* leave the repository in a clean working state

The implementation must not depend on quirks unique to one coding agent.

---

# 84. MOST IMPORTANT PRODUCT PRINCIPLE

The goal is NOT:

> "Make the existing website open in a desktop window."

The goal is:

> **Transform AI LinkedIn Manager into a genuine local-first, open-source desktop software product while keeping the existing server deployment capability and preserving the safety-first agent architecture.**

Think through every architectural consequence of that sentence.

---

# 85. START NOW

Start with:

```text
PHASE 0 — COMPLETE REPOSITORY AUDIT
```

Do not begin the desktop implementation before understanding the repository.

Read the code and current documentation, produce the audit, identify contradictions, propose the target architecture, and then proceed systematically through the migration phases.

Do not stop after generating a plan.

Once the audit and architecture are validated against the repository itself, continue executing the migration phase by phase, fixing tests and documentation as you go, until the repository satisfies the Definition of Done above.
