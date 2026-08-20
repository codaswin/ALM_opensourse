"""Deployment-mode contract shared by hosted and desktop runtimes.

This module deliberately describes *varying infrastructure capabilities* only.
Approval enforcement, the model-router choke point, guardrails, the kill switch,
and cost/rate policies are shared business invariants and are not runtime flags.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

RUNTIME_MODE_ENV = "AI_LINKEDIN_RUNTIME_MODE"
APP_DATA_DIR_ENV = "AI_LINKEDIN_APP_DATA_DIR"

_profile: RuntimeProfile | None = None


class RuntimeConfigurationError(ValueError):
    """Raised when the selected runtime cannot be configured safely."""


class RuntimeMode(StrEnum):
    SERVER = "server"
    DESKTOP = "desktop"


class IdentityStrategy(StrEnum):
    SERVER_SESSION = "server_session"
    LOCAL_OWNER = "local_owner"


class DatabaseBackend(StrEnum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class StateBackend(StrEnum):
    REDIS = "redis"
    SQLITE = "sqlite"


class CredentialBackend(StrEnum):
    ENCRYPTED_DATABASE = "encrypted_database"
    OS_KEYRING = "os_keyring"


@dataclass(frozen=True)
class RuntimeCapabilities:
    requires_login: bool
    supports_multiple_users: bool
    supports_user_administration: bool
    uses_distributed_scheduler_coordination: bool
    runs_scheduler_only_while_app_is_open: bool


@dataclass(frozen=True)
class RuntimeProfile:
    mode: RuntimeMode
    identity: IdentityStrategy
    database: DatabaseBackend
    state: StateBackend
    credentials: CredentialBackend
    capabilities: RuntimeCapabilities
    app_data_dir: Path | None

    @property
    def is_desktop(self) -> bool:
        return self.mode is RuntimeMode.DESKTOP

    @property
    def is_server(self) -> bool:
        return self.mode is RuntimeMode.SERVER


def parse_runtime_mode(value: str | None) -> RuntimeMode:
    """Parse an explicit mode, preserving hosted behavior as the default."""
    normalized = (value or RuntimeMode.SERVER.value).strip().lower()
    try:
        return RuntimeMode(normalized)
    except ValueError as exc:
        supported = ", ".join(mode.value for mode in RuntimeMode)
        raise RuntimeConfigurationError(
            f"Unsupported {RUNTIME_MODE_ENV}={value!r}; expected one of: {supported}"
        ) from exc


def build_runtime_profile(environ: Mapping[str, str] | None = None) -> RuntimeProfile:
    """Build the immutable runtime boundary from an environment mapping.

    Desktop paths must be supplied by the native owner process. Requiring an
    absolute path prevents packaged builds from writing user data relative to
    an installer directory or an unpredictable working directory.
    """
    env = os.environ if environ is None else environ
    mode = parse_runtime_mode(env.get(RUNTIME_MODE_ENV))

    if mode is RuntimeMode.SERVER:
        return RuntimeProfile(
            mode=mode,
            identity=IdentityStrategy.SERVER_SESSION,
            database=DatabaseBackend.POSTGRESQL,
            state=StateBackend.REDIS,
            credentials=CredentialBackend.ENCRYPTED_DATABASE,
            capabilities=RuntimeCapabilities(
                requires_login=True,
                supports_multiple_users=True,
                supports_user_administration=True,
                uses_distributed_scheduler_coordination=True,
                runs_scheduler_only_while_app_is_open=False,
            ),
            app_data_dir=None,
        )

    raw_app_data_dir = env.get(APP_DATA_DIR_ENV, "").strip()
    if not raw_app_data_dir:
        raise RuntimeConfigurationError(
            f"{APP_DATA_DIR_ENV} is required when {RUNTIME_MODE_ENV}=desktop"
        )
    app_data_dir = Path(raw_app_data_dir).expanduser()
    if not app_data_dir.is_absolute():
        raise RuntimeConfigurationError(f"{APP_DATA_DIR_ENV} must be an absolute path")

    return RuntimeProfile(
        mode=mode,
        identity=IdentityStrategy.LOCAL_OWNER,
        database=DatabaseBackend.SQLITE,
        state=StateBackend.SQLITE,
        credentials=CredentialBackend.OS_KEYRING,
        capabilities=RuntimeCapabilities(
            requires_login=False,
            supports_multiple_users=False,
            supports_user_administration=False,
            uses_distributed_scheduler_coordination=False,
            runs_scheduler_only_while_app_is_open=True,
        ),
        app_data_dir=app_data_dir,
    )


def get_runtime_profile() -> RuntimeProfile:
    """Return the process runtime profile, constructed once on first use."""
    global _profile
    if _profile is None:
        _profile = build_runtime_profile()
    return _profile


def configure_runtime_profile(profile: RuntimeProfile) -> None:
    """Install an explicit profile before services start (also used by tests)."""
    global _profile
    _profile = profile


def reset_runtime_profile() -> None:
    """Forget the cached profile so changed startup configuration can be read."""
    global _profile
    _profile = None
