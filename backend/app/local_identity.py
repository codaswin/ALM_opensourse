"""Stable one-owner identity for a personal desktop installation."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass

from app.application_paths import ApplicationPaths
from app.models.auth import DashboardUserRecord
from sqlalchemy.ext.asyncio import AsyncSession

_IDENTITY_FILENAME = "installation.json"
_LOCAL_USERNAME = "local-owner"
_LOCAL_ROLE = "operator"


@dataclass(frozen=True)
class LocalIdentity:
    installation_id: str
    user_id: str
    username: str = _LOCAL_USERNAME
    role: str = _LOCAL_ROLE


def load_or_create_local_identity(paths: ApplicationPaths) -> LocalIdentity:
    paths.ensure_exists()
    identity_file = paths.config_dir / _IDENTITY_FILENAME
    try:
        payload = json.loads(identity_file.read_text(encoding="utf-8"))
        installation_id = str(uuid.UUID(str(payload["installation_id"])))
    except FileNotFoundError:
        installation_id = str(uuid.uuid4())
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(identity_file, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump({"installation_id": installation_id, "format_version": 1}, stream)
            stream.write("\n")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Desktop installation identity is invalid: {identity_file}. "
            "Restore it from backup or use the explicit reset flow."
        ) from exc

    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"ai-linkedin-manager:{installation_id}:local-owner"))
    return LocalIdentity(installation_id=installation_id, user_id=user_id)


async def ensure_local_owner(db: AsyncSession, identity: LocalIdentity) -> DashboardUserRecord:
    existing = await db.get(DashboardUserRecord, identity.user_id)
    if existing is not None:
        if existing.username != identity.username or existing.role != identity.role:
            raise RuntimeError("Desktop local-owner record conflicts with the installation identity")
        return existing

    owner = DashboardUserRecord(
        id=identity.user_id,
        username=identity.username,
        password_hash="desktop-local-owner:no-password-login",
        role=identity.role,
        active=True,
    )
    db.add(owner)
    await db.commit()
    await db.refresh(owner)
    return owner
