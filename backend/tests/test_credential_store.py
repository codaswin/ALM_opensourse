from __future__ import annotations

import pytest
from app.credential_store import OSKeyringCredentialStore
from app.memory import platform_credentials
from app.models.auth import DashboardUserRecord
from app.models.platform_credential import PlatformCredentialRecord
from app.runtime import (
    APP_DATA_DIR_ENV,
    RUNTIME_MODE_ENV,
    build_runtime_profile,
    configure_runtime_profile,
    reset_runtime_profile,
)


class _FakeKeyring:
    priority = 1.0

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


def test_os_keyring_store_is_installation_and_user_scoped() -> None:
    backend = _FakeKeyring()
    first = OSKeyringCredentialStore("install-a", backend)
    second = OSKeyringCredentialStore("install-b", backend)

    first.set("user-a", "OPENAI_API_KEY", "secret-a")
    first.set("user-b", "OPENAI_API_KEY", "secret-b")

    assert first.get("user-a", "OPENAI_API_KEY") == "secret-a"
    assert first.get("user-b", "OPENAI_API_KEY") == "secret-b"
    assert second.get("user-a", "OPENAI_API_KEY") is None
    first.delete("user-a", "OPENAI_API_KEY")
    assert first.get("user-a", "OPENAI_API_KEY") is None


def test_os_keyring_store_rejects_empty_values() -> None:
    store = OSKeyringCredentialStore("install-a", _FakeKeyring())
    with pytest.raises(ValueError, match="cannot be empty"):
        store.set("user-a", "OPENAI_API_KEY", "")


async def test_desktop_platform_credentials_never_store_secret_in_sqlite(
    db_session, tmp_path
) -> None:
    profile = build_runtime_profile(
        {RUNTIME_MODE_ENV: "desktop", APP_DATA_DIR_ENV: str(tmp_path)}
    )
    configure_runtime_profile(profile)
    store = OSKeyringCredentialStore("install-a", _FakeKeyring())
    platform_credentials.configure_desktop_store(store)
    user = DashboardUserRecord(
        id="desktop-owner-id",
        username="desktop-owner",
        password_hash="desktop-local-owner:no-password-login",
        role="operator",
        active=True,
    )
    db_session.add(user)
    await db_session.commit()
    try:
        await platform_credentials.save_platform_credentials(
            db_session, user.id, "openai", {"api_key": "desktop-secret"}
        )
        record = await db_session.get(
            PlatformCredentialRecord, f"{user.id}:openai:api_key"
        )
        assert record is not None
        assert record.encrypted_value is None
        assert store.get(user.id, "OPENAI_API_KEY") == "desktop-secret"
    finally:
        platform_credentials.configure_desktop_store(None)
        reset_runtime_profile()
