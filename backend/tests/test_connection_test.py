from __future__ import annotations

import pytest
from app.tenancy import context as tenancy_context
from app.tenancy import credentials as tenancy_credentials
from app.tools import composio_client, connection_test
from app.llmops import anthropic_client, openai_client

_USER = "connection-test-user"


@pytest.fixture(autouse=True)
def _tenancy_context() -> None:
    tenancy_credentials.clear_user(_USER)
    token = tenancy_context.set_current_user_id(_USER)
    yield
    tenancy_context.reset_current_user_id(token)
    tenancy_credentials.clear_user(_USER)


@pytest.fixture(autouse=True)
def _clear_client_caches() -> None:
    anthropic_client.reset_client_cache()
    openai_client.reset_client_cache()
    composio_client.reset_client_cache()
    yield
    anthropic_client.reset_client_cache()
    openai_client.reset_client_cache()
    composio_client.reset_client_cache()


def test_testable_platforms_covers_every_provider_with_a_live_check() -> None:
    assert connection_test.testable_platforms() == {
        "anthropic",
        "openai",
        "composio",
        "github",
        "reddit",
        "producthunt",
    }


async def test_anthropic_missing_key_reports_missing_without_network() -> None:
    result = await connection_test.test_platform_connection("anthropic")
    assert result == {
        "platform_id": "anthropic",
        "status": "missing",
        "detail": "ANTHROPIC_API_KEY is not set. Set it on the Connections page before using route_and_call.",
    }


async def test_openai_missing_key_reports_missing_without_network() -> None:
    result = await connection_test.test_platform_connection("openai")
    assert result == {
        "platform_id": "openai",
        "status": "missing",
        "detail": "OPENAI_API_KEY is not set. Set it on the Connections page before using route_and_call.",
    }


async def test_composio_missing_key_reports_missing_without_network() -> None:
    result = await connection_test.test_platform_connection("composio")
    assert result == {
        "platform_id": "composio",
        "status": "missing",
        "detail": "COMPOSIO_API_KEY is not set. Set it in the Connections page before using any Composio-backed tool.",
    }


async def test_reddit_missing_credentials_reports_missing_without_network() -> None:
    result = await connection_test.test_platform_connection("reddit")
    assert result["platform_id"] == "reddit"
    assert result["status"] == "missing"


async def test_producthunt_missing_token_reports_missing_without_network() -> None:
    result = await connection_test.test_platform_connection("producthunt")
    assert result["platform_id"] == "producthunt"
    assert result["status"] == "missing"


async def test_unknown_platform_reports_unavailable() -> None:
    result = await connection_test.test_platform_connection("linkedin")
    assert result == {
        "platform_id": "linkedin",
        "status": "unavailable",
        "detail": "This platform has no live connectivity check yet.",
    }
