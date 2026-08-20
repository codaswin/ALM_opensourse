from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.config import settings
from app.runtime import get_runtime_profile
from app.runtime_state import AsyncSQLiteStateClient, SQLiteStateClient
from app.shared_state import get_client as get_shared_state_client
from app.tenancy.context import get_current_user_id

_client: Redis | AsyncSQLiteStateClient | None = None


def get_client() -> Redis | AsyncSQLiteStateClient:
    global _client
    if _client is None:
        if get_runtime_profile().is_desktop:
            shared_client = get_shared_state_client()
            if not isinstance(shared_client, SQLiteStateClient):
                raise RuntimeError("Desktop runtime state client is not SQLite-backed")
            _client = AsyncSQLiteStateClient(shared_client)
        else:
            _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def configure_client(client: Redis | AsyncSQLiteStateClient) -> None:
    """Override the module-level Redis client — used by tests to inject a fake/in-memory client."""
    global _client
    _client = client


def reset_client() -> None:
    global _client
    _client = None


async def _get(key: str) -> dict[str, Any] | None:
    raw = await get_client().get(key)
    return json.loads(raw) if raw else None


async def _set(key: str, data: dict[str, Any], ttl_seconds: int | None = None) -> None:
    await get_client().set(key, json.dumps(data), ex=ttl_seconds or settings.WORKING_MEMORY_TTL_SECONDS)


async def _clear(key: str) -> None:
    await get_client().delete(key)


async def get_current_draft(task_id: str) -> dict[str, Any] | None:
    return await _get(f"working:draft:{get_current_user_id()}:{task_id}")


async def set_current_draft(task_id: str, draft: dict[str, Any], ttl_seconds: int | None = None) -> None:
    await _set(f"working:draft:{get_current_user_id()}:{task_id}", draft, ttl_seconds)


async def clear_current_draft(task_id: str) -> None:
    await _clear(f"working:draft:{get_current_user_id()}:{task_id}")


async def get_current_thread(thread_id: str) -> dict[str, Any] | None:
    return await _get(f"working:thread:{get_current_user_id()}:{thread_id}")


async def set_current_thread(thread_id: str, thread_state: dict[str, Any], ttl_seconds: int | None = None) -> None:
    await _set(f"working:thread:{get_current_user_id()}:{thread_id}", thread_state, ttl_seconds)


async def clear_current_thread(thread_id: str) -> None:
    await _clear(f"working:thread:{get_current_user_id()}:{thread_id}")


async def get_approval_session(session_id: str) -> dict[str, Any] | None:
    return await _get(f"working:approval_session:{get_current_user_id()}:{session_id}")


async def set_approval_session(session_id: str, session_state: dict[str, Any], ttl_seconds: int | None = None) -> None:
    await _set(f"working:approval_session:{get_current_user_id()}:{session_id}", session_state, ttl_seconds)


async def clear_approval_session(session_id: str) -> None:
    await _clear(f"working:approval_session:{get_current_user_id()}:{session_id}")
