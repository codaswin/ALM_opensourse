from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone

from redis.exceptions import WatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_setting import AgentSetting
from app.shared_state import get_client
from app.tenancy import rate_limits as rate_limit_overrides
from app.tenancy.context import get_current_user_id


class RateLimitConfigError(RuntimeError):
    pass


class RateLimitExceededError(RuntimeError):
    pass


# Falls back to the same conservative defaults documented in .env.example
# when unset, mirroring llmops/cost_tracker.py's _budget_usd() — desktop
# installs never populate these from a .env file (there isn't one bundled;
# see backend/desktop_entry.py), so requiring them to be set unconditionally
# meant every approval-gated LinkedIn action failed on first use for every
# desktop user. An env var still explicitly set (including by a self-hosted
# operator) always overrides its default; anything not in this table keeps
# failing loud, same as before.
_DEFAULT_DAILY_CAPS: dict[str, int] = {
    "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY": 3,
    "LINKEDIN_API_RATE_LIMIT_DELETES_DAILY": 3,
    "LINKEDIN_API_RATE_LIMIT_REPLIES_DAILY": 20,
    "LINKEDIN_API_RATE_LIMIT_CONNECTIONS_DAILY": 5,
    "LINKEDIN_API_RATE_LIMIT_LIKES_DAILY": 20,
}

# The durable (agent_settings) key each env var's per-user override is
# stored under — see app.tenancy.rate_limits for the in-memory overlay
# these durable rows are replayed into (load_all_saved_rate_limits below),
# and main.py's /rate-limits endpoints for where a user edits them.
RATE_LIMIT_SETTING_KEYS: dict[str, str] = {
    "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY": "linkedin_rate_limit.posts_daily",
    "LINKEDIN_API_RATE_LIMIT_DELETES_DAILY": "linkedin_rate_limit.deletes_daily",
    "LINKEDIN_API_RATE_LIMIT_REPLIES_DAILY": "linkedin_rate_limit.replies_daily",
    "LINKEDIN_API_RATE_LIMIT_CONNECTIONS_DAILY": "linkedin_rate_limit.connections_daily",
    "LINKEDIN_API_RATE_LIMIT_LIKES_DAILY": "linkedin_rate_limit.likes_daily",
}


def _cap(env_var: str) -> int:
    override = rate_limit_overrides.get_override(get_current_user_id(), env_var)
    if override is not None:
        return override
    raw = os.environ.get(env_var)
    if raw is None or raw == "":
        default = _DEFAULT_DAILY_CAPS.get(env_var)
        if default is None:
            raise RateLimitConfigError(f"{env_var} is not set; refusing to run without a configured daily rate cap.")
        return default
    try:
        cap = int(raw)
    except ValueError as exc:
        raise RateLimitConfigError(f"{env_var} must be an integer, got {raw!r}") from exc
    if cap < 0:
        raise RateLimitConfigError(f"{env_var} must be >= 0, got {cap}")
    return cap


async def load_all_saved_rate_limits(db: AsyncSession) -> None:
    """Replay every user's saved daily-limit overrides back into the

    in-process overlay (app.tenancy.rate_limits) — agent_settings rows are
    the durable copy, but _cap() reads the overlay, not the DB, so a
    process restart needs this to not lose what was configured.
    """
    setting_key_to_env_var = {key: env_var for env_var, key in RATE_LIMIT_SETTING_KEYS.items()}
    result = await db.execute(
        select(AgentSetting).where(AgentSetting.key.in_(setting_key_to_env_var.keys()))
    )
    values_by_user: dict[str, dict[str, int]] = {}
    for row in result.scalars().all():
        env_var = setting_key_to_env_var[row.key]
        try:
            values_by_user.setdefault(row.user_id, {})[env_var] = int(row.value)
        except ValueError:
            continue
    rate_limit_overrides.load_overlay(values_by_user)


def _key(action: str) -> str:
    # Namespaced per user (the configured cap in env_var still applies as
    # the same numeric limit to everyone, but each user's usage against it
    # is counted independently — see plans/peaceful-scribbling-tiger.md
    # Stage 3) so one user maxing out publish_post never blocks another.
    return f"safety:rate:{get_current_user_id()}:{datetime.now(timezone.utc):%Y-%m-%d}:{action}"


def _ttl() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return max(60, int((tomorrow - now).total_seconds()) + 60)


class DailyRateLimiter:
    def check_and_increment(self, action: str, env_var: str) -> int:
        cap = _cap(env_var)
        client = get_client()
        key = _key(action)
        while True:
            try:
                with client.pipeline() as pipe:
                    pipe.watch(key)
                    used = int(pipe.get(key) or 0)
                    if used >= cap:
                        pipe.unwatch()
                        raise RateLimitExceededError(
                            f"Daily rate cap for '{action}' reached ({used}/{cap}, set via {env_var})."
                        )
                    pipe.multi()
                    pipe.set(key, used + 1, ex=_ttl())
                    pipe.execute()
                    return used + 1
            except WatchError:
                continue

    def peek(self, action: str, env_var: str) -> tuple[int, int]:
        cap = _cap(env_var)
        return int(get_client().get(_key(action)) or 0), cap

    def reset(self) -> None:
        client = get_client()
        keys = list(client.scan_iter(match="safety:rate:*"))
        if keys:
            client.delete(*keys)


daily_rate_limiter = DailyRateLimiter()
