"""Credential storage contracts for hosted and desktop runtimes."""

from __future__ import annotations

import sys
from typing import Protocol


class CredentialStoreUnavailable(RuntimeError):
    pass


class KeyringBackend(Protocol):
    @property
    def priority(self) -> float: ...

    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class CredentialStore(Protocol):
    def get(self, user_id: str, name: str) -> str | None: ...

    def set(self, user_id: str, name: str, value: str) -> None: ...

    def delete(self, user_id: str, name: str) -> None: ...


def _system_keyring_backend() -> KeyringBackend:
    try:
        import keyring
    except ImportError as exc:
        raise CredentialStoreUnavailable("The native keyring package is not bundled") from exc

    backend = keyring.get_keyring()
    backend_name = f"{backend.__class__.__module__}.{backend.__class__.__name__}".lower()
    priority = float(getattr(backend, "priority", 0))
    if priority <= 0 or any(marker in backend_name for marker in ("fail", "plaintext", "null")):
        raise CredentialStoreUnavailable("No secure operating-system credential store is available")

    if sys.platform.startswith("linux") and not any(
        marker in backend_name for marker in ("secretservice", "kwallet", "chainer")
    ):
        raise CredentialStoreUnavailable(
            f"Unsupported Linux keyring backend {backend_name!r}; Secret Service or KWallet is required"
        )
    return backend


class OSKeyringCredentialStore:
    def __init__(self, installation_id: str, backend: KeyringBackend | None = None) -> None:
        self._service = f"ai-linkedin-manager/{installation_id}"
        self._backend = backend or _system_keyring_backend()

    def _account(self, user_id: str, name: str) -> str:
        return f"{user_id}:{name}"

    def get(self, user_id: str, name: str) -> str | None:
        return self._backend.get_password(self._service, self._account(user_id, name))

    def set(self, user_id: str, name: str, value: str) -> None:
        if not value:
            raise ValueError("Credential value cannot be empty")
        self._backend.set_password(self._service, self._account(user_id, name), value)

    def delete(self, user_id: str, name: str) -> None:
        try:
            self._backend.delete_password(self._service, self._account(user_id, name))
        except Exception as exc:
            if exc.__class__.__name__ != "PasswordDeleteError":
                raise
