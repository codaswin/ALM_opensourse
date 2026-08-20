from pathlib import Path

import pytest
from app.runtime import (
    APP_DATA_DIR_ENV,
    RUNTIME_MODE_ENV,
    CredentialBackend,
    DatabaseBackend,
    IdentityStrategy,
    RuntimeConfigurationError,
    RuntimeMode,
    StateBackend,
    build_runtime_profile,
    configure_runtime_profile,
    get_runtime_profile,
    parse_runtime_mode,
    reset_runtime_profile,
)


def test_server_profile_is_the_compatibility_default() -> None:
    profile = build_runtime_profile({})

    assert profile.mode is RuntimeMode.SERVER
    assert profile.identity is IdentityStrategy.SERVER_SESSION
    assert profile.database is DatabaseBackend.POSTGRESQL
    assert profile.state is StateBackend.REDIS
    assert profile.credentials is CredentialBackend.ENCRYPTED_DATABASE
    assert profile.app_data_dir is None
    assert profile.is_server is True
    assert profile.is_desktop is False
    assert profile.capabilities.requires_login is True
    assert profile.capabilities.supports_multiple_users is True
    assert profile.capabilities.supports_user_administration is True
    assert profile.capabilities.uses_distributed_scheduler_coordination is True
    assert profile.capabilities.runs_scheduler_only_while_app_is_open is False


def test_desktop_profile_has_one_local_owner_and_local_backends(tmp_path: Path) -> None:
    profile = build_runtime_profile(
        {
            RUNTIME_MODE_ENV: "desktop",
            APP_DATA_DIR_ENV: str(tmp_path),
        }
    )

    assert profile.mode is RuntimeMode.DESKTOP
    assert profile.identity is IdentityStrategy.LOCAL_OWNER
    assert profile.database is DatabaseBackend.SQLITE
    assert profile.state is StateBackend.SQLITE
    assert profile.credentials is CredentialBackend.OS_KEYRING
    assert profile.app_data_dir == tmp_path
    assert profile.is_desktop is True
    assert profile.is_server is False
    assert profile.capabilities.requires_login is False
    assert profile.capabilities.supports_multiple_users is False
    assert profile.capabilities.supports_user_administration is False
    assert profile.capabilities.uses_distributed_scheduler_coordination is False
    assert profile.capabilities.runs_scheduler_only_while_app_is_open is True


@pytest.mark.parametrize("value", ["SERVER", " server ", None])
def test_runtime_mode_parser_preserves_server_default(value: str | None) -> None:
    assert parse_runtime_mode(value) is RuntimeMode.SERVER


def test_desktop_profile_requires_an_explicit_absolute_data_path(tmp_path: Path) -> None:
    with pytest.raises(RuntimeConfigurationError, match=APP_DATA_DIR_ENV):
        build_runtime_profile({RUNTIME_MODE_ENV: "desktop"})

    with pytest.raises(RuntimeConfigurationError, match="absolute path"):
        build_runtime_profile(
            {
                RUNTIME_MODE_ENV: "desktop",
                APP_DATA_DIR_ENV: "relative/data",
            }
        )

    assert tmp_path.is_absolute()


def test_unknown_runtime_mode_fails_closed() -> None:
    with pytest.raises(RuntimeConfigurationError, match="Unsupported"):
        build_runtime_profile({RUNTIME_MODE_ENV: "portable"})


def test_explicit_runtime_profile_is_process_stable(tmp_path: Path) -> None:
    desktop = build_runtime_profile(
        {RUNTIME_MODE_ENV: "desktop", APP_DATA_DIR_ENV: str(tmp_path)}
    )
    configure_runtime_profile(desktop)
    try:
        assert get_runtime_profile() is desktop
    finally:
        reset_runtime_profile()
