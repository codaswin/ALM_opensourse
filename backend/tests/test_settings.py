from __future__ import annotations

import asyncio

import pytest
from app.database import Base, configure_engine
from app.memory.settings import get_setting, set_setting
from app.models.agent_setting import AgentSetting  # noqa: F401
from app.tenancy import context as tenancy_context
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture(autouse=True)
def _tenancy_context():
    token = tenancy_context.set_current_user_id("settings-test-user")
    yield
    tenancy_context.reset_current_user_id(token)


async def test_concurrent_first_writes_to_the_same_key_never_crash(tmp_path) -> None:
    """Regression guard: two concurrent PUTs of a brand-new setting key

    (e.g. a rapid double-click on a "Save" button, such as the Connections
    page's per-user rate-limit fields) used to raise an unhandled
    IntegrityError — both requests see no existing row via db.get() and
    both try to INSERT the same (user_id, key) composite primary key.
    Needs a real file (not :memory:, which multiplexes concurrent sessions
    over a single shared connection and doesn't reproduce the race) so two
    independent sessions genuinely race against the same durable data.
    """
    db_path = tmp_path / "settings_race.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    configure_engine(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def save(value: str) -> None:
        async with factory() as session:
            await set_setting(session, "linkedin_rate_limit.posts_daily", value, updated_by="test")

    try:
        results = await asyncio.gather(save("5"), save("7"), return_exceptions=True)
        assert results == [None, None], f"a concurrent first write raised: {results}"

        async with factory() as session:
            final_value = await get_setting(session, "linkedin_rate_limit.posts_daily")
        assert final_value in {"5", "7"}  # one write wins cleanly; both are acceptable outcomes
    finally:
        await engine.dispose()
