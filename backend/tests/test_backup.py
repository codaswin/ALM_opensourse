from __future__ import annotations

from pathlib import Path

from app.application_paths import ApplicationPaths
from app.backup import create_backup, list_backups
from app.runtime import APP_DATA_DIR_ENV, RUNTIME_MODE_ENV, build_runtime_profile


def _paths(tmp_path: Path) -> ApplicationPaths:
    profile = build_runtime_profile({RUNTIME_MODE_ENV: "desktop", APP_DATA_DIR_ENV: str(tmp_path)})
    paths = ApplicationPaths.for_desktop(profile)
    paths.ensure_exists()
    return paths


def test_create_backup_on_empty_workspace_still_succeeds(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    manifest = create_backup(paths)
    assert manifest.includes_database is False
    assert manifest.includes_runtime_state is False
    assert manifest.includes_rag is False
    assert (paths.backups_dir / manifest.name).is_dir()


def test_create_backup_copies_database_and_rag(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    import sqlite3

    with sqlite3.connect(paths.database_file) as db:
        db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        db.commit()
    (paths.rag_dir / "some-workspace").mkdir(parents=True)
    (paths.rag_dir / "some-workspace" / "CURRENT").write_text("generation-1")

    manifest = create_backup(paths)

    assert manifest.includes_database is True
    assert manifest.includes_rag is True
    backup_dir = paths.backups_dir / manifest.name
    assert (backup_dir / "app.sqlite3").exists()
    assert (backup_dir / "rag" / "some-workspace" / "CURRENT").read_text() == "generation-1"
    assert manifest.size_bytes > 0


def test_create_backup_never_copies_credentials_or_config(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    (paths.config_dir / "runtime.json").write_text("{}")

    manifest = create_backup(paths)

    backup_dir = paths.backups_dir / manifest.name
    assert not (backup_dir / "config").exists()
    assert not (backup_dir / "runtime.json").exists()


def test_list_backups_returns_newest_first(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    first = create_backup(paths)
    second = create_backup(paths)

    manifests = list_backups(paths)

    assert [m.name for m in manifests][:2] == sorted([first.name, second.name], reverse=True)


def test_list_backups_on_fresh_workspace_is_empty(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    assert list_backups(paths) == []
