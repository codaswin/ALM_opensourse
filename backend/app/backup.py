"""User-triggered workspace backups for desktop mode.

`desktop_migrations._backup_database` already makes an automatic backup
before every schema migration — this module adds an explicit, user-visible
"back up now" action (desktopv.md #29: "Design a safe abstraction for
Export Backup / Restore Backup").

Restore is intentionally NOT automated here: swapping the live
SQLite/runtime-state files out from under a running FastAPI process (open
connections, an active scheduler, an open state-store connection) needs the
app closed first, so it stays a documented manual procedure — copy the
chosen backup's files back over database/app.sqlite3, state/runtime.sqlite3,
and rag/ while the app is not running. desktopv.md #29 explicitly allows
this ("if backup implementation is beyond the first milestone, design/
document it and mark it clearly") for restore specifically.

Never touches credentials — those live only in the OS keyring (see
docs/security-model.md), never in any file this module copies.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.application_paths import ApplicationPaths


class BackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupManifest:
    name: str
    created_at: str
    includes_database: bool
    includes_runtime_state: bool
    includes_rag: bool
    size_bytes: int


def _copy_sqlite_db(source: Path, destination: Path) -> bool:
    if not source.exists() or source.stat().st_size == 0:
        return False
    with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as backup_db:
        source_db.backup(backup_db)
    return True


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def create_backup(paths: ApplicationPaths) -> BackupManifest:
    paths.ensure_exists()
    # Microsecond resolution, not just seconds: two backups triggered in
    # quick succession (a doubled UI click, an automated test) must not
    # collide on the destination directory name.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = paths.backups_dir / f"backup-{timestamp}"
    try:
        destination.mkdir(parents=True, exist_ok=False)
        includes_database = _copy_sqlite_db(paths.database_file, destination / "app.sqlite3")
        includes_runtime_state = _copy_sqlite_db(paths.runtime_state_file, destination / "runtime.sqlite3")
        includes_rag = paths.rag_dir.exists() and any(paths.rag_dir.iterdir())
        if includes_rag:
            shutil.copytree(paths.rag_dir, destination / "rag")
    except Exception as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise BackupError(f"Could not create backup ({exc.__class__.__name__}: {exc})") from exc
    return BackupManifest(
        name=destination.name,
        created_at=timestamp,
        includes_database=includes_database,
        includes_runtime_state=includes_runtime_state,
        includes_rag=includes_rag,
        size_bytes=_dir_size(destination),
    )


def list_backups(paths: ApplicationPaths) -> list[BackupManifest]:
    if not paths.backups_dir.exists():
        return []
    manifests: list[BackupManifest] = []
    for entry in sorted(paths.backups_dir.iterdir(), reverse=True):
        if not entry.is_dir() or not entry.name.startswith("backup-"):
            continue
        manifests.append(
            BackupManifest(
                name=entry.name,
                created_at=entry.name.removeprefix("backup-"),
                includes_database=(entry / "app.sqlite3").exists(),
                includes_runtime_state=(entry / "runtime.sqlite3").exists(),
                includes_rag=(entry / "rag").exists(),
                size_bytes=_dir_size(entry),
            )
        )
    return manifests
