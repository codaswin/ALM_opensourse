"""Backup-first Alembic migration runner for the desktop SQLite database."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.application_paths import ApplicationPaths


class DesktopMigrationError(RuntimeError):
    pass


def _backup_database(paths: ApplicationPaths) -> Path | None:
    source = paths.database_file
    if not source.exists() or source.stat().st_size == 0:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = paths.backups_dir / f"app-before-migration-{timestamp}.sqlite3"
    try:
        with sqlite3.connect(source) as source_db, sqlite3.connect(destination) as backup_db:
            source_db.backup(backup_db)
    except sqlite3.Error as exc:
        destination.unlink(missing_ok=True)
        raise DesktopMigrationError("Could not create a safe database backup before migration") from exc
    backups = sorted(
        paths.backups_dir.glob("app-before-migration-*.sqlite3"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for stale in backups[5:]:
        stale.unlink(missing_ok=True)
    return destination


def run_desktop_migrations(paths: ApplicationPaths, database_url: str) -> Path | None:
    paths.ensure_exists()
    backup = _backup_database(paths)
    backend_dir = Path(__file__).resolve().parents[1]
    configuration_file = backend_dir / "alembic.ini"
    migrations_dir = backend_dir / "alembic"
    if not configuration_file.exists() or not migrations_dir.exists():
        raise DesktopMigrationError("Bundled database migration resources are missing")
    configuration = Config(str(configuration_file))
    configuration.set_main_option("script_location", str(migrations_dir))
    configuration.set_main_option("sqlalchemy.url", database_url)
    configuration.attributes["database_url"] = database_url
    try:
        command.upgrade(configuration, "head")
    except Exception as exc:
        raise DesktopMigrationError(
            f"Database migration failed ({exc.__class__.__name__}: {exc}). "
            f"The pre-migration backup is {backup!s}."
        ) from exc
    return backup
