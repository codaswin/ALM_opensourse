"""Runtime-state client selected by the immutable deployment profile."""

from __future__ import annotations

from redis import Redis

from app.config import settings
from app.application_paths import ApplicationPaths
from app.runtime import get_runtime_profile
from app.runtime_state import SQLiteStateClient

_client: Redis | SQLiteStateClient | None = None


def get_client() -> Redis | SQLiteStateClient:
    global _client
    if _client is None:
        profile = get_runtime_profile()
        if profile.is_desktop:
            paths = ApplicationPaths.for_desktop(profile)
            paths.ensure_exists()
            _client = SQLiteStateClient(paths.runtime_state_file)
        else:
            _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def configure_client(client: Redis | SQLiteStateClient) -> None:
    global _client
    _client = client


def reset_client() -> None:
    global _client
    if isinstance(_client, SQLiteStateClient):
        _client.close()
    _client = None
