from pathlib import Path
import asyncio

from app.application_paths import ApplicationPaths
from app.desktop_migrations import run_desktop_migrations
from app.runtime import APP_DATA_DIR_ENV, RUNTIME_MODE_ENV, build_runtime_profile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def _paths(root: Path) -> ApplicationPaths:
    return ApplicationPaths.for_desktop(
        build_runtime_profile(
            {RUNTIME_MODE_ENV: "desktop", APP_DATA_DIR_ENV: str(root)}
        )
    )


async def test_desktop_migrations_create_current_schema_and_backup_on_upgrade(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    url = f"sqlite+aiosqlite:///{paths.database_file}"
    assert await asyncio.to_thread(run_desktop_migrations, paths, url) is None

    engine = create_async_engine(url)
    async with engine.connect() as connection:
        revision = (
            await connection.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
    await engine.dispose()
    assert revision == "20260821_0011"

    backup = await asyncio.to_thread(run_desktop_migrations, paths, url)
    assert backup is not None
    assert backup.exists()
    assert backup.stat().st_size > 0
