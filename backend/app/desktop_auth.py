"""Authentication for the Tauri-owned loopback API."""

from __future__ import annotations

import hmac
import os

from app.local_identity import LocalIdentity
from app.safety.api_auth import AuthenticatedUser
from fastapi import HTTPException, Request

LAUNCH_TOKEN_ENV = "AI_LINKEDIN_LAUNCH_TOKEN"


def configured_launch_token() -> str:
    token = os.environ.get(LAUNCH_TOKEN_ENV, "")
    if len(token) < 32:
        raise RuntimeError(
            f"{LAUNCH_TOKEN_ENV} must contain a high-entropy per-launch token of at least 32 characters"
        )
    return token


def authenticate_desktop_request(request: Request, identity: LocalIdentity) -> AuthenticatedUser:
    authorization = request.headers.get("Authorization", "")
    scheme, _, supplied = authorization.partition(" ")
    expected = configured_launch_token()
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Desktop application authentication required")
    user = AuthenticatedUser(identity.user_id, identity.username, identity.role)
    request.state.auth_user = user
    return user
