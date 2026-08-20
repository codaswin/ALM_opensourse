"""Installation-scoped writable paths derived from the runtime profile."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.runtime import RuntimeProfile


@dataclass(frozen=True)
class ApplicationPaths:
    root: Path
    database_dir: Path
    state_dir: Path
    rag_dir: Path
    logs_dir: Path
    backups_dir: Path
    cache_dir: Path
    config_dir: Path

    @classmethod
    def for_desktop(cls, profile: RuntimeProfile) -> ApplicationPaths:
        if not profile.is_desktop or profile.app_data_dir is None:
            raise ValueError("Desktop application paths require a desktop runtime profile")
        root = profile.app_data_dir
        return cls(
            root=root,
            database_dir=root / "database",
            state_dir=root / "state",
            rag_dir=root / "rag",
            logs_dir=root / "logs",
            backups_dir=root / "backups",
            cache_dir=root / "cache",
            config_dir=root / "config",
        )

    @property
    def database_file(self) -> Path:
        return self.database_dir / "app.sqlite3"

    @property
    def runtime_state_file(self) -> Path:
        return self.state_dir / "runtime.sqlite3"

    def ensure_exists(self) -> None:
        for directory in (
            self.database_dir,
            self.state_dir,
            self.rag_dir,
            self.logs_dir,
            self.backups_dir,
            self.cache_dir,
            self.config_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
