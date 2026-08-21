"""FastAPI serving layer — an HTTP surface over infrastructure that already

exists and is fully tested elsewhere (memory.settings, safety.approval_gate,
learning.proposal_review, llmops.cost_tracker). This file adds no new
business logic of its own; every endpoint is a thin wrapper.

This is what the PRP's "exposed via a FastAPI endpoint for the future
dashboard UI" (memory-agent, Phase 1) and the Post-MVP "dashboard UI control"
roadmap item build against — the API exists now, a UI can point at it later
without this file changing.

Every `= Depends(get_db)` default below is ruff bugbear rule B008's
canonical false positive: FastAPI's own dependency-injection idiom, not the
mutable-default-argument bug that rule exists to catch. Silenced once here
rather than per line.
"""

# ruff: noqa: B008

from __future__ import annotations

import os
import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Literal

import structlog
from app import activity as activity_module
from app.application_paths import ApplicationPaths
from app.database import get_session, get_session_factory, init_models
from app.desktop_auth import authenticate_desktop_request
from app.desktop_migrations import run_desktop_migrations
from app.config import settings
from app.learning import proposal_review
from app.learning.proposal_review import (
    ProposalAlreadyDecidedError,
    ProposalNotFoundError,
)
from app.learning.scheduler import get_scheduler, start_scheduler, stop_scheduler
from app.llmops.anthropic_client import AnthropicConfigError
from app.llmops.hermes_client import HermesCallError
from app.llmops.openai_client import OpenAIConfigError
from app.memory import brand_voice as brand_voice_memory
from app.memory import platform_credentials
from app.local_identity import ensure_local_owner, load_or_create_local_identity
from app.memory.settings import get_setting, set_setting
from app.safety import approval_gate, kill_switch
from app.safety.approval_gate import (
    ApprovalRequestAlreadyDecidedError,
    ApprovalRequestNotFoundError,
    SystemPausedError,
)
from app.safety.api_auth import (
    authorize_request,
    current_user,
    is_public_path,
)
from app.safety.secrets import CredentialEncryptionError
from app import backup as backup_module
from app import shared_state
from app.rag.ingest import VectorStore
from app.runtime import get_runtime_profile
from app.tenancy.context import reset_current_user_id, set_current_user_id
from app.tenancy.paths import user_vector_store_path
from app.tools import connection_test
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


def _recovery_error(
    *, code: str, message: str, retryable: bool, action: str
) -> dict[str, Any]:
    return {
        "detail": message,
        "code": code,
        "retryable": retryable,
        "action": action,
        "return_route": "/workflows",
        "correlation_id": str(uuid.uuid4()),
    }


def _production_mode() -> bool:
    return os.environ.get("PRODUCTION_MODE", "false").lower() in {"1", "true", "yes"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Every tools/*.py module registers itself with tools.registry as a side
    # effect of being imported — nothing imports them at process startup
    # otherwise, so every execute_tool() call (every workflow trigger, every
    # approval execution) would silently fail with "Unknown tool" without
    # this. Every other entrypoint (pytest fixtures, safety.audit's CLI)
    # already does this explicitly; the live server needs the same call.
    from app.tools.registry import _import_all_tools

    _import_all_tools()
    profile = get_runtime_profile()
    if profile.is_desktop:
        paths = ApplicationPaths.for_desktop(profile)
        paths.ensure_exists()
        await asyncio.to_thread(run_desktop_migrations, paths, settings.DATABASE_URL)
    elif os.environ.get("AUTO_CREATE_SCHEMA", "").lower() in {"1", "true", "yes"}:
        await init_models()
    # Replay anything saved through the Connections page back into
    # os.environ — the DB row is the durable copy, but every credential
    # consumer (anthropic_client, search_reddit, ...) still just reads
    # os.environ, so a restart needs this to not lose what was configured.
    async with get_session_factory()() as session:
        if profile.is_desktop:
            identity = load_or_create_local_identity(ApplicationPaths.for_desktop(profile))
            await ensure_local_owner(session, identity)
            app.state.desktop_identity = identity
        await platform_credentials.load_all_saved_credentials(session)
    start_scheduler()
    logger.info("app_startup_complete")
    yield
    stop_scheduler()
    logger.info("app_shutdown_complete")


app = FastAPI(
    title="AI LinkedIn Manager",
    description="Runtime API for agent settings, the human-approval queue, and the self-learning review queue.",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None if _production_mode() else "/docs",
    redoc_url=None if _production_mode() else "/redoc",
    openapi_url=None if _production_mode() else "/openapi.json",
)

@app.middleware("http")
async def _dashboard_session_guard(request: Request, call_next):
    if request.method.upper() == "OPTIONS" or is_public_path(request.url.path):
        return await call_next(request)
    try:
        profile = get_runtime_profile()
        if profile.is_desktop:
            user = authenticate_desktop_request(request, request.app.state.desktop_identity)
        else:
            # Self-hosted/server-mode login lived here; that deployment now
            # lives in a separate repository, so this build has no way to
            # authenticate a non-desktop request.
            raise HTTPException(status_code=501, detail="Server mode is not available in this build")
        authorize_request(request, user)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    # Every credential lookup, cached SDK client, and scoped query downstream
    # of this point asks "who's the current user" via this context var
    # instead of a parameter threaded through every function — see
    # app.tenancy.context.
    token = set_current_user_id(user.id)
    try:
        return await call_next(request)
    finally:
        reset_current_user_id(token)


# The dashboard frontend (frontend/, a separate Vite dev server / static
# build) runs on a different origin than this API, so it needs CORS
# explicitly enabled. Defaults cover Vite's dev-server ports; override via
# CORS_ALLOWED_ORIGINS (comma-separated) for a real deployment's actual
# frontend origin — never widen this to "*" once credentials/cookies are
# in play.
#
# Registered AFTER _dashboard_session_guard (not before): Starlette wraps
# middleware in the order they're added, each new one OUTSIDE the previous —
# so whichever call comes last ends up outermost. With CORSMiddleware added
# first (innermost), every 401 the guard returns for an unauthenticated
# request short-circuited entirely inside the guard, never reaching
# CORSMiddleware to get an Access-Control-Allow-Origin header — the browser
# then reports a CORS failure instead of a real 401, and the login page
# itself couldn't call /auth/login. Registering CORS last makes it the
# outermost layer so it can decorate every response, including the guard's.
_DEFAULT_CORS_ORIGINS = (
    "tauri://localhost,http://tauri.localhost,http://localhost:5173,http://127.0.0.1:5173"
    if get_runtime_profile().is_desktop
    else "http://localhost:5173,http://127.0.0.1:5173"
)
_cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Any endpoint that can trigger a real model call (the /workflows/* triggers,
# /learning/reflect) fails loudly rather than a bare 500 when no live model
# is configured — 503 "unavailable" is the honest status for "this needs a
# dependency that isn't set up," not a server bug.
@app.exception_handler(AnthropicConfigError)
async def _anthropic_config_error_handler(request: Request, exc: AnthropicConfigError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_recovery_error(
            code="credential.anthropic_unavailable",
            message=f"Anthropic client not available: {exc}",
            retryable=False,
            action="open_connections",
        ),
    )


@app.exception_handler(HermesCallError)
async def _hermes_call_error_handler(request: Request, exc: HermesCallError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_recovery_error(
            code="dependency.hermes_unavailable",
            message=f"Hermes/vLLM worker not available: {exc}",
            retryable=True,
            action="retry",
        ),
    )


@app.exception_handler(OpenAIConfigError)
async def _openai_config_error_handler(request: Request, exc: OpenAIConfigError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_recovery_error(
            code="credential.openai_unavailable",
            message=f"OpenAI client not available: {exc}",
            retryable=False,
            action="open_connections",
        ),
    )


@app.exception_handler(CredentialEncryptionError)
async def _credential_encryption_error_handler(request: Request, exc: CredentialEncryptionError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content=_recovery_error(
            code="credential.encryption_unavailable",
            message=str(exc),
            retryable=False,
            action="open_connections",
        ),
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session
# ---------------------------------------------------------------------------
# Dashboard authentication — desktop-only. The frontend still calls /auth/me
# to learn who the current (single, local-owner) user is; there is no
# password login, no session cookie, and no admin user-invite in this build
# (that belonged to self-hosted/server mode, which now lives in a separate
# repository).
# ---------------------------------------------------------------------------


@app.get("/auth/me")
async def auth_me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    return {"user": {"id": user.id, "username": user.username, "role": user.role}, "csrf_token": None}


@app.post("/auth/logout")
async def logout(request: Request) -> dict[str, bool]:
    return {"logged_out": True}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runtime/bootstrap")
async def runtime_bootstrap(request: Request) -> dict[str, Any]:
    profile = get_runtime_profile()
    user = current_user(request)
    return {
        "mode": profile.mode.value,
        "user": {"id": user.id, "username": user.username, "role": user.role},
        "capabilities": {
            "requires_login": profile.capabilities.requires_login,
            "supports_multiple_users": profile.capabilities.supports_multiple_users,
            "supports_user_administration": profile.capabilities.supports_user_administration,
            "uses_distributed_scheduler_coordination": (
                profile.capabilities.uses_distributed_scheduler_coordination
            ),
            "runs_scheduler_only_while_app_is_open": (
                profile.capabilities.runs_scheduler_only_while_app_is_open
            ),
        },
        "api_version": app.version,
    }


@app.get("/diagnostics")
async def diagnostics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """One place to see whether every backing service actually works.

    Desktop and hosted both swap real infrastructure behind the runtime
    profile (SQLite/Redis, OS keyring/encrypted rows, ...) — this probes
    each one live instead of assuming "the process started" means "every
    dependency is healthy" (desktopv.md #31; the audit's "no diagnostic
    view" gap). Never returns storage paths or secret values.
    """
    profile = get_runtime_profile()
    components: dict[str, dict[str, Any]] = {"backend": {"status": "ok"}}

    try:
        await db.execute(text("SELECT 1"))
        components["database"] = {"status": "ok", "backend": profile.database.value}
    except Exception as exc:
        components["database"] = {"status": "error", "backend": profile.database.value, "detail": exc.__class__.__name__}

    try:
        client = shared_state.get_client()
        client.set("diagnostics:probe", "1", ex=5)
        client.get("diagnostics:probe")
        components["runtime_state"] = {"status": "ok", "backend": profile.state.value}
    except Exception as exc:
        components["runtime_state"] = {"status": "error", "backend": profile.state.value, "detail": exc.__class__.__name__}

    scheduler = get_scheduler()
    components["scheduler"] = {"status": "running" if (scheduler is not None and scheduler.running) else "stopped"}

    try:
        store = VectorStore(user_vector_store_path())
        components["vector_store"] = {"status": "ok", "chunks": store.count()}
    except Exception as exc:
        components["vector_store"] = {"status": "error", "detail": exc.__class__.__name__}

    components["credential_store"] = {"status": "ok", "backend": profile.credentials.value}
    components["kill_switch"] = dict(kill_switch.get_pause_info())

    return {"mode": profile.mode.value, "components": components}


@app.get("/backup")
async def list_backups() -> list[dict[str, Any]]:
    """Desktop-only — hosted deployments back up PostgreSQL/Redis at the

    infrastructure level (docs/data-boundaries.md), so this is always empty
    in server mode rather than an error.
    """
    profile = get_runtime_profile()
    if not profile.is_desktop:
        return []
    paths = ApplicationPaths.for_desktop(profile)
    manifests = await asyncio.to_thread(backup_module.list_backups, paths)
    return [asdict(m) for m in manifests]


@app.post("/backup")
async def create_backup_now() -> dict[str, Any]:
    profile = get_runtime_profile()
    if not profile.is_desktop:
        raise HTTPException(
            status_code=409,
            detail="Hosted deployments back up PostgreSQL/Redis at the infrastructure level — use your database operator's backup process instead.",
        )
    paths = ApplicationPaths.for_desktop(profile)
    try:
        manifest = await asyncio.to_thread(backup_module.create_backup, paths)
    except backup_module.BackupError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return asdict(manifest)


@app.get("/activity")
async def read_activity() -> dict[str, Any] | None:
    """Polled by the dashboard's ActivityBanner every ~1.2s — None means idle."""
    return activity_module.get_activity()


# ---------------------------------------------------------------------------
# Agent settings — e.g. research_agent.poll_interval, editable without a redeploy
# ---------------------------------------------------------------------------


class SettingUpdate(BaseModel):
    value: str


class PauseSystemBody(BaseModel):
    reason: str


@app.get("/system/status")
async def system_status() -> dict[str, Any]:
    return kill_switch.get_pause_info()


@app.post("/system/pause")
async def pause_system(body: PauseSystemBody, request: Request) -> dict[str, Any]:
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="A pause reason is required")
    kill_switch.pause_system(reason=reason, paused_by=current_user(request).username)
    return kill_switch.get_pause_info()


@app.post("/system/resume")
async def resume_system(request: Request) -> dict[str, Any]:
    kill_switch.resume_system(resumed_by=current_user(request).username)
    return kill_switch.get_pause_info()


@app.get("/settings/{key}")
async def read_setting(key: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    value = await get_setting(db, key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"No value or default registered for setting {key!r}")
    return {"key": key, "value": value}


@app.put("/settings/{key}")
async def update_setting(
    key: str, body: SettingUpdate, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    record = await set_setting(db, key, body.value, updated_by=current_user(request).username)
    return {"key": record.key, "value": record.value, "updated_by": record.updated_by, "updated_at": record.updated_at}


# ---------------------------------------------------------------------------
# Brand voice — titled profiles, stored in the Content Writer/Engagement
# Agents' semantic memory (RAG "brand_voice" source) as well as listed here
# ---------------------------------------------------------------------------


def _brand_voice_dict(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "title": record.title,
        "content": record.content,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


class BrandVoiceCreate(BaseModel):
    title: str
    content: str


@app.get("/brand-voice")
async def list_brand_voice(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    records = await brand_voice_memory.list_brand_voices(db)
    return [_brand_voice_dict(r) for r in records]


@app.post("/brand-voice")
async def create_brand_voice(body: BrandVoiceCreate, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        record = await brand_voice_memory.create_brand_voice(db, title=body.title, content=body.content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _brand_voice_dict(record)


@app.get("/brand-voice/{brand_voice_id}")
async def read_brand_voice(brand_voice_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    record = await brand_voice_memory.get_brand_voice(db, brand_voice_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No brand voice with id {brand_voice_id!r}")
    return _brand_voice_dict(record)


@app.put("/brand-voice/{brand_voice_id}")
async def update_brand_voice(
    brand_voice_id: str, body: BrandVoiceCreate, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        record = await brand_voice_memory.update_brand_voice(
            db, brand_voice_id, title=body.title, content=body.content
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail=f"No brand voice with id {brand_voice_id!r}")
    return _brand_voice_dict(record)


@app.delete("/brand-voice/{brand_voice_id}")
async def delete_brand_voice(brand_voice_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    deleted = await brand_voice_memory.delete_brand_voice(db, brand_voice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No brand voice with id {brand_voice_id!r}")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Connections — where a human pastes API keys/tokens/OAuth IDs for every
# platform this system talks to, instead of hand-editing .env. See
# memory/platform_credentials.py's PLATFORM_SCHEMA for what each platform
# needs and why; this file only wraps it as HTTP.
# ---------------------------------------------------------------------------


@app.get("/credentials")
async def list_credentials(request: Request, db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return await platform_credentials.list_platform_status(db, current_user(request).id)


class CredentialSaveBody(BaseModel):
    values: dict[str, str]


@app.put("/credentials/{platform_id}")
async def save_credentials(
    platform_id: str, body: CredentialSaveBody, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    user_id = current_user(request).id
    try:
        await platform_credentials.save_platform_credentials(db, user_id, platform_id, body.values)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    statuses = await platform_credentials.list_platform_status(db, user_id)
    return next(s for s in statuses if s["id"] == platform_id)


@app.delete("/credentials/{platform_id}")
async def clear_credentials(platform_id: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    try:
        deleted = await platform_credentials.delete_platform_credentials(db, current_user(request).id, platform_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"deleted": deleted}


@app.post("/credentials/{platform_id}/test")
async def test_credentials(platform_id: str) -> dict[str, Any]:
    """Actually calls the provider — "saved" and "working" are different claims.

    Only reads the already-loaded per-user credential overlay/cached SDK
    client; never logs or returns the credential value itself.
    """
    return dict(await connection_test.test_platform_connection(platform_id))


# ---------------------------------------------------------------------------
# Approval queue
# ---------------------------------------------------------------------------


class DecisionBody(BaseModel):
    reason: str | None = None


@app.get("/approvals")
async def list_approvals(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    pending = await approval_gate.list_actionable(db)
    return [p.model_dump(mode="json") for p in pending]


@app.post("/approvals/{approval_id}/approve")
async def approve_approval(
    approval_id: str, body: DecisionBody, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        return await approval_gate.approve(db, approval_id, decided_by=current_user(request).username)
    except SystemPausedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalRequestAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/retry")
async def retry_approval(
    approval_id: str, body: DecisionBody, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        return await approval_gate.retry(db, approval_id, decided_by=current_user(request).username)
    except SystemPausedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalRequestAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/reject")
async def reject_approval(
    approval_id: str, body: DecisionBody, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        record = await approval_gate.reject(
            db, approval_id, decided_by=current_user(request).username, reason=body.reason
        )
    except ApprovalRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalRequestAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return record.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Manual workflow triggers — each wraps an existing agent entrypoint with
# app.activity's reporting (via the agent modules themselves) so the
# dashboard's ActivityBanner shows real-time progress. None of these add new
# agent logic — they only wire an HTTP request to the same functions the
# scheduler/other call sites already use.
# ---------------------------------------------------------------------------


class ResearchWorkflowBody(BaseModel):
    query: str
    sources: list[str] | None = None
    limit_per_source: int = 10


@app.post("/workflows/research")
async def trigger_research_workflow(body: ResearchWorkflowBody) -> dict[str, Any]:
    """Synthesis-free — no live model required, so this works even without

    ANTHROPIC_API_KEY configured (Hacker News/RSS/DuckDuckGo need no key at
    all; Reddit/GitHub/Product Hunt degrade gracefully if uncredentialed).
    """
    from app.agents.research_pipeline import research

    try:
        results = await research(body.query, sources=body.sources, limit_per_source=body.limit_per_source)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"query": body.query, "result_count": len(results), "results": results}


class ContentWorkflowBody(BaseModel):
    calendar_entries: list[str] = []
    recent_post_topics: list[str] = []


@app.post("/workflows/content")
async def trigger_content_workflow(body: ContentWorkflowBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Content Strategist -> Content Writer, chained: the brief the

    Strategist produces is fed straight into the Writer, landing either in
    the approval queue or flagged needs_human_rewrite — same outcome as the
    two agents running back-to-back in production.
    """
    from app.agents.content_strategist import build_post_brief
    from app.agents.content_writer import write_post
    from app.llmops.model_router import route_and_call

    brief = await build_post_brief(body.recent_post_topics, body.calendar_entries, route_and_call)
    result = await write_post(brief.model_dump(mode="json"), route_and_call, db=db)
    return {"brief": brief.model_dump(mode="json"), **result}


class AnalyticsWorkflowBody(BaseModel):
    period_start: date | None = None
    period_end: date | None = None


@app.post("/workflows/analytics")
async def trigger_analytics_workflow(body: AnalyticsWorkflowBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.agents.analytics import generate_weekly_digest
    from app.llmops.model_router import route_and_call

    period_end = body.period_end or date.today()
    period_start = body.period_start or (period_end - timedelta(days=7))
    digest = await generate_weekly_digest(db, route_and_call, period_start, period_end)
    return digest.model_dump(mode="json")


class EngagementWorkflowBody(BaseModel):
    notification_type: Literal["comment", "dm", "connection_request"]
    text: str
    notification_id: str = "manual-trigger"


@app.post("/workflows/engagement")
async def trigger_engagement_workflow(body: EngagementWorkflowBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.agents.engagement import handle_notification
    from app.llmops.model_router import route_and_call

    notification = {"id": body.notification_id, "type": body.notification_type, "text": body.text}
    return await handle_notification(notification, route_and_call, db=db)


# ---------------------------------------------------------------------------
# Self-learning review queue
# ---------------------------------------------------------------------------


@app.get("/learning/proposals")
async def list_learning_proposals(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    pending = await proposal_review.list_pending(db)
    return [p.model_dump(mode="json") for p in pending]


@app.post("/learning/proposals/{proposal_id}/approve")
async def approve_learning_proposal(
    proposal_id: str, body: DecisionBody, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        record = await proposal_review.approve_proposal(
            db, proposal_id, decided_by=current_user(request).username
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProposalAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/learning/proposals/{proposal_id}/reject")
async def reject_learning_proposal(
    proposal_id: str, body: DecisionBody, request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    try:
        record = await proposal_review.reject_proposal(
            db, proposal_id, decided_by=current_user(request).username, reason=body.reason
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProposalAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return record.model_dump(mode="json")


class ReflectBody(BaseModel):
    days: int = 7


@app.post("/learning/reflect")
async def trigger_reflection(body: ReflectBody, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """On-demand reflection run — the scheduler (learning/scheduler.py) fires

    this same job weekly by default; this endpoint exists for manual/testing
    triggers between scheduled runs.
    """
    from app.learning.reflection_job import run_reflection
    from app.llmops.model_router import route_and_call

    result = await run_reflection(db, route_and_call, days=body.days)
    return {**result, "proposals": [p.model_dump(mode="json") for p in result["proposals"]]}


# ---------------------------------------------------------------------------
# Cost observability
# ---------------------------------------------------------------------------


@app.get("/cost")
async def cost_summary() -> dict[str, float]:
    from app.llmops.cost_tracker import get_cost_summary

    return get_cost_summary()
