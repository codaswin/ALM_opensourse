"""Live connectivity checks for saved platform credentials.

`platform_credentials.list_platform_status` only reports "a value is
stored" — it never calls the provider, so a revoked/typo'd/expired key
looks identical to a working one until a real workflow run fails on it
(see the Composio "Invalid API key" incident this project has already hit
once). This module actually calls each provider with the cheapest possible
authenticated request so Connections can show `connected` / `invalid` /
`missing` / `unavailable` instead of just "a value is stored" — the
`missing` / `invalid` / `expired` / `unavailable` vocabulary desktopv.md
asks for (`docs/data-boundaries.md`'s "Connection metadata" contract).

Every check reuses the same cached, per-user SDK client each agent call
already goes through (`anthropic_client`, `openai_client`,
`composio_client`) — this never opens a second, untracked client.
"""

from __future__ import annotations

import typing as t
from typing import Literal, TypedDict

import anthropic
import httpx
import openai
import structlog

from app.llmops import anthropic_client, openai_client
from app.tenancy.credentials import resolve_credential
from app.tools import composio_client
from app.tools.search_producthunt import GRAPHQL_URL as _PRODUCTHUNT_GRAPHQL_URL
from app.tools.search_producthunt import ProductHuntConfigError, _require_token as _require_producthunt_token
from app.tools.search_reddit import RedditConfigError, _fetch_access_token as _fetch_reddit_token

logger = structlog.get_logger(__name__)

ConnectionState = Literal["connected", "invalid", "missing", "unavailable"]


class ConnectionTestResult(TypedDict):
    platform_id: str
    status: ConnectionState
    detail: str


def _result(platform_id: str, status: ConnectionState, detail: str) -> ConnectionTestResult:
    return {"platform_id": platform_id, "status": status, "detail": detail}


async def _test_anthropic() -> ConnectionTestResult:
    try:
        client = anthropic_client._get_client()
    except anthropic_client.AnthropicConfigError as exc:
        return _result("anthropic", "missing", str(exc))
    try:
        await client.models.list(limit=1)
    except anthropic.AuthenticationError:
        return _result("anthropic", "invalid", "Anthropic rejected this API key.")
    except anthropic.APIError as exc:
        return _result("anthropic", "unavailable", f"Anthropic is unreachable ({exc.__class__.__name__}).")
    return _result("anthropic", "connected", "Anthropic API key is valid.")


async def _test_openai() -> ConnectionTestResult:
    try:
        client = openai_client._get_client()
    except openai_client.OpenAIConfigError as exc:
        return _result("openai", "missing", str(exc))
    try:
        await client.models.list()
    except openai.AuthenticationError:
        return _result("openai", "invalid", "OpenAI rejected this API key.")
    except openai.APIError as exc:
        return _result("openai", "unavailable", f"OpenAI is unreachable ({exc.__class__.__name__}).")
    return _result("openai", "connected", "OpenAI API key is valid.")


async def _test_composio() -> ConnectionTestResult:
    try:
        client = composio_client.get_composio_client()
    except composio_client.ComposioConfigError as exc:
        return _result("composio", "missing", str(exc))
    try:
        import asyncio

        await asyncio.to_thread(client.toolkits.get, slug="linkedin")
    except Exception as exc:  # Composio's SDK does not expose typed auth exceptions.
        message = str(exc)
        if "401" in message or "InvalidAPIKey" in message:
            return _result("composio", "invalid", "Composio rejected this API key.")
        return _result("composio", "unavailable", f"Composio is unreachable ({exc.__class__.__name__}).")
    return _result("composio", "connected", "Composio API key is valid.")


async def _test_github() -> ConnectionTestResult:
    token = resolve_credential("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-linkedin-manager-research-agent"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get("https://api.github.com/rate_limit", headers=headers)
    except httpx.HTTPError as exc:
        return _result("github", "unavailable", f"GitHub is unreachable ({exc.__class__.__name__}).")
    if response.status_code == 401:
        return _result("github", "invalid", "GitHub rejected this token.")
    if response.status_code != 200:
        return _result("github", "unavailable", f"GitHub returned HTTP {response.status_code}.")
    if not token:
        return _result("github", "connected", "No token set — using GitHub's public (unauthenticated) rate limit.")
    return _result("github", "connected", "GitHub token is valid.")


async def _test_reddit() -> ConnectionTestResult:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await _fetch_reddit_token(client)
    except RedditConfigError as exc:
        return _result("reddit", "missing", str(exc))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            return _result("reddit", "invalid", "Reddit rejected this client ID/secret.")
        return _result("reddit", "unavailable", f"Reddit returned HTTP {exc.response.status_code}.")
    except httpx.HTTPError as exc:
        return _result("reddit", "unavailable", f"Reddit is unreachable ({exc.__class__.__name__}).")
    return _result("reddit", "connected", "Reddit credentials are valid.")


async def _test_producthunt() -> ConnectionTestResult:
    try:
        token = _require_producthunt_token()
    except ProductHuntConfigError as exc:
        return _result("producthunt", "missing", str(exc))
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                _PRODUCTHUNT_GRAPHQL_URL,
                json={"query": "{ viewer { user { id } } }"},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        return _result("producthunt", "unavailable", f"Product Hunt is unreachable ({exc.__class__.__name__}).")
    if response.status_code == 401:
        return _result("producthunt", "invalid", "Product Hunt rejected this token.")
    if response.status_code != 200:
        return _result("producthunt", "unavailable", f"Product Hunt returned HTTP {response.status_code}.")
    return _result("producthunt", "connected", "Product Hunt token is valid.")


_TESTERS: dict[str, t.Callable[[], t.Awaitable[ConnectionTestResult]]] = {
    "anthropic": _test_anthropic,
    "openai": _test_openai,
    "composio": _test_composio,
    "github": _test_github,
    "reddit": _test_reddit,
    "producthunt": _test_producthunt,
}


def testable_platforms() -> frozenset[str]:
    return frozenset(_TESTERS)


async def test_platform_connection(platform_id: str) -> ConnectionTestResult:
    tester = _TESTERS.get(platform_id)
    if tester is None:
        return _result(platform_id, "unavailable", "This platform has no live connectivity check yet.")
    try:
        return await tester()
    except Exception as exc:  # Never let a provider's SDK crash the status endpoint.
        logger.warning("connection_test_unexpected_error", platform_id=platform_id, error=exc.__class__.__name__)
        return _result(platform_id, "unavailable", f"Could not verify this connection ({exc.__class__.__name__}).")
