from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request

_PUBLIC_PATH_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")
Role = Literal["viewer", "operator", "admin"]
_ROLE_LEVEL = {"viewer": 10, "operator": 20, "admin": 30}


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    username: str
    role: Role


def is_public_path(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in _PUBLIC_PATH_PREFIXES)


def current_user(request: Request) -> AuthenticatedUser:
    user = getattr(request.state, "auth_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_role(request: Request, minimum: Role = "viewer") -> AuthenticatedUser:
    user = current_user(request)
    if _ROLE_LEVEL[user.role] < _ROLE_LEVEL[minimum]:
        raise HTTPException(status_code=403, detail=f"{minimum} role required")
    return user


def authorize_request(request: Request, user: AuthenticatedUser) -> None:
    # Credentials, approvals, brand voice, etc. are scoped to request.state's
    # current user (see app.tenancy.context), so a "viewer" role can safely
    # read/manage their OWN data here.
    method = request.method.upper()
    minimum: Role = "viewer" if method in {"GET", "HEAD", "OPTIONS"} else "operator"
    if _ROLE_LEVEL[user.role] < _ROLE_LEVEL[minimum]:
        raise HTTPException(status_code=403, detail=f"{minimum} role required")
