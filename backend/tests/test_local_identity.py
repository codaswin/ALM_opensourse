from pathlib import Path

import pytest
from app.application_paths import ApplicationPaths
from app.local_identity import ensure_local_owner, load_or_create_local_identity
from app.runtime import APP_DATA_DIR_ENV, RUNTIME_MODE_ENV, build_runtime_profile


def _paths(root: Path) -> ApplicationPaths:
    profile = build_runtime_profile(
        {RUNTIME_MODE_ENV: "desktop", APP_DATA_DIR_ENV: str(root)}
    )
    return ApplicationPaths.for_desktop(profile)


def test_local_identity_is_stable_and_installation_scoped(tmp_path: Path) -> None:
    first = load_or_create_local_identity(_paths(tmp_path / "first"))
    again = load_or_create_local_identity(_paths(tmp_path / "first"))
    second = load_or_create_local_identity(_paths(tmp_path / "second"))

    assert first == again
    assert first.user_id != second.user_id
    assert first.installation_id != second.installation_id


def test_corrupt_local_identity_fails_without_resetting_data(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    paths.ensure_exists()
    (paths.config_dir / "installation.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Restore it from backup"):
        load_or_create_local_identity(paths)


async def test_local_owner_is_idempotently_persisted(db_session, tmp_path: Path) -> None:
    identity = load_or_create_local_identity(_paths(tmp_path))
    first = await ensure_local_owner(db_session, identity)
    second = await ensure_local_owner(db_session, identity)

    assert first.id == identity.user_id
    assert second.id == identity.user_id
    assert first.username == "local-owner"
    assert first.role == "operator"
