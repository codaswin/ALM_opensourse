from pathlib import Path

import pytest
from app.desktop_auth import LAUNCH_TOKEN_ENV
from app.local_identity import LocalIdentity
from app.main import app
from app.runtime import (
    APP_DATA_DIR_ENV,
    RUNTIME_MODE_ENV,
    build_runtime_profile,
    configure_runtime_profile,
    reset_runtime_profile,
)
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def desktop_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    token = "desktop-test-token-with-at-least-32-characters"
    profile = build_runtime_profile(
        {RUNTIME_MODE_ENV: "desktop", APP_DATA_DIR_ENV: str(tmp_path)}
    )
    configure_runtime_profile(profile)
    monkeypatch.setenv(LAUNCH_TOKEN_ENV, token)
    app.state.desktop_identity = LocalIdentity(
        installation_id="desktop-test-installation",
        user_id="desktop-test-owner",
    )
    yield token
    reset_runtime_profile()


async def test_desktop_api_requires_launch_token(desktop_runtime: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/runtime/bootstrap")).status_code == 401
        assert (
            await client.get(
                "/runtime/bootstrap", headers={"Authorization": "Bearer incorrect-token"}
            )
        ).status_code == 401


async def test_desktop_api_skips_password_login_and_returns_local_owner(
    desktop_runtime: str,
) -> None:
    headers = {"Authorization": f"Bearer {desktop_runtime}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as client:
        bootstrap = await client.get("/runtime/bootstrap")
        assert bootstrap.status_code == 200
        assert bootstrap.json()["mode"] == "desktop"
        assert bootstrap.json()["user"]["id"] == "desktop-test-owner"
        assert bootstrap.json()["capabilities"]["requires_login"] is False

        session = await client.get("/auth/me")
        assert session.status_code == 200
        assert session.json()["csrf_token"] is None
        login = await client.post("/auth/login", json={"username": "x", "password": "y"})
        assert login.status_code == 404
