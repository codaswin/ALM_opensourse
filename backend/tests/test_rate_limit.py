from __future__ import annotations

import pytest
from app.memory.settings import set_setting
from app.models.agent_setting import AgentSetting  # noqa: F401
from app.tenancy import context as tenancy_context
from app.tenancy import rate_limits as rate_limit_overrides
from app.tools.rate_limit import (
    RateLimitConfigError,
    RateLimitExceededError,
    daily_rate_limiter,
    load_all_saved_rate_limits,
)


@pytest.fixture(autouse=True)
def _tenancy_context():
    token = tenancy_context.set_current_user_id("rate-limit-test-user")
    yield
    tenancy_context.reset_current_user_id(token)
    rate_limit_overrides.load_overlay({})


def test_check_and_increment_counts_up_to_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_RATE_LIMIT_CAP", "2")
    assert daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP") == 1
    assert daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP") == 2
    with pytest.raises(RateLimitExceededError):
        daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP")


def test_each_user_gets_their_own_independent_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression guard: the Redis counter key used to be shared across every

    user (one global daily cap for the whole deployment) — see
    plans/peaceful-scribbling-tiger.md Stage 3. User A maxing out their cap
    must never block user B at the same configured limit.
    """
    monkeypatch.setenv("TEST_RATE_LIMIT_CAP", "1")

    token_a = tenancy_context.set_current_user_id("rate-limit-user-a")
    try:
        assert daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP") == 1
        with pytest.raises(RateLimitExceededError):
            daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP")
    finally:
        tenancy_context.reset_current_user_id(token_a)

    token_b = tenancy_context.set_current_user_id("rate-limit-user-b")
    try:
        # User B is unaffected by user A having already exhausted their cap.
        assert daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP") == 1
    finally:
        tenancy_context.reset_current_user_id(token_b)


def test_known_linkedin_rate_limit_env_vars_fall_back_to_documented_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Desktop installs never populate a .env file (see desktop_entry.py),

    so every one of these must have a working built-in default — otherwise
    every approval-gated LinkedIn action fails on first use for every
    desktop user, regardless of which action they approve first.
    """
    monkeypatch.delenv("LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", raising=False)
    used, cap = daily_rate_limiter.peek("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")
    assert (used, cap) == (0, 3)


def test_explicit_env_var_still_overrides_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", "7")
    _, cap = daily_rate_limiter.peek("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")
    assert cap == 7


def test_unrecognized_env_var_still_fails_loud_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_RATE_LIMIT_CAP", raising=False)
    with pytest.raises(RateLimitConfigError, match="is not set"):
        daily_rate_limiter.check_and_increment("do_thing", "TEST_RATE_LIMIT_CAP")


def test_invalid_explicit_value_still_fails_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", "not-a-number")
    with pytest.raises(RateLimitConfigError, match="must be an integer"):
        daily_rate_limiter.check_and_increment("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")


def test_per_user_override_beats_both_env_var_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", "7")
    rate_limit_overrides.set_override("rate-limit-test-user", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", 1)
    assert daily_rate_limiter.check_and_increment("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY") == 1
    with pytest.raises(RateLimitExceededError):
        daily_rate_limiter.check_and_increment("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")


def test_per_user_override_never_affects_another_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", "5")
    rate_limit_overrides.set_override("rate-limit-user-a", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY", 1)

    token_a = tenancy_context.set_current_user_id("rate-limit-user-a")
    try:
        _, cap_a = daily_rate_limiter.peek("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")
        assert cap_a == 1
    finally:
        tenancy_context.reset_current_user_id(token_a)

    token_b = tenancy_context.set_current_user_id("rate-limit-user-b")
    try:
        _, cap_b = daily_rate_limiter.peek("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")
        assert cap_b == 5  # untouched by user A's override
    finally:
        tenancy_context.reset_current_user_id(token_b)


def test_clear_override_reverts_to_env_var_default() -> None:
    rate_limit_overrides.set_override("rate-limit-test-user", "LINKEDIN_API_RATE_LIMIT_LIKES_DAILY", 2)
    _, cap = daily_rate_limiter.peek("like_post", "LINKEDIN_API_RATE_LIMIT_LIKES_DAILY")
    assert cap == 2

    rate_limit_overrides.clear_override("rate-limit-test-user", "LINKEDIN_API_RATE_LIMIT_LIKES_DAILY")
    _, cap = daily_rate_limiter.peek("like_post", "LINKEDIN_API_RATE_LIMIT_LIKES_DAILY")
    assert cap == 20  # built-in default


async def test_load_all_saved_rate_limits_replays_durable_settings_into_the_overlay(db_session) -> None:
    await set_setting(db_session, "linkedin_rate_limit.posts_daily", "9", updated_by="test")

    rate_limit_overrides.load_overlay({})  # simulate a fresh process with nothing loaded yet
    await load_all_saved_rate_limits(db_session)

    _, cap = daily_rate_limiter.peek("publish_post", "LINKEDIN_API_RATE_LIMIT_POSTS_DAILY")
    assert cap == 9
