"""Per-user LinkedIn daily rate-limit overrides — the replacement for a

single env var applying the same numeric cap to every user. A value saved
by one user is never visible to or applied against another. Nothing set
here for a given (user_id, env_var) means "fall back to the env var / the
built-in default" — see `app.tools.rate_limit._cap`.

Deliberately dependency-free (no app.memory/app.models imports), mirroring
`app.tenancy.credentials` — this module is imported by `app.tools.rate_limit`,
which stays free of any import cycle with the settings-storage layer that
persists these values durably.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_overlay: dict[str, dict[str, int]] = {}


def set_override(user_id: str, env_var: str, cap: int) -> None:
    with _lock:
        _overlay.setdefault(user_id, {})[env_var] = cap


def clear_override(user_id: str, env_var: str) -> None:
    with _lock:
        _overlay.get(user_id, {}).pop(env_var, None)


def load_overlay(values_by_user: dict[str, dict[str, int]]) -> None:
    """Bulk (re)population at startup — replaces the whole overlay wholesale."""
    with _lock:
        _overlay.clear()
        for user_id, values in values_by_user.items():
            _overlay[user_id] = dict(values)


def get_override(user_id: str, env_var: str) -> int | None:
    with _lock:
        return _overlay.get(user_id, {}).get(env_var)
