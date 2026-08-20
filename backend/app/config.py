import os

from dotenv import load_dotenv
from pydantic import BaseModel

from app.application_paths import ApplicationPaths
from app.runtime import get_runtime_profile

# Loads repo-root .env into os.environ before any Settings/os.getenv() read
# happens. config.py is imported early enough in every run path (tests,
# CLI tools, the future FastAPI app) that this is the one place that needs
# it — every other module's os.environ.get() calls (e.g. the research
# tools' REDDIT_CLIENT_ID etc.) then just see it already populated.
load_dotenv()


def normalize_async_database_url(url: str) -> str:
    """Map common provider URLs to SQLAlchemy's async dialects."""
    replacements = (
        ("postgres://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
        ("sqlite://", "sqlite+aiosqlite://"),
    )
    for prefix, replacement in replacements:
        if url.startswith(prefix):
            return replacement + url[len(prefix):]
    return url


_runtime_profile = get_runtime_profile()
if _runtime_profile.is_desktop:
    _desktop_paths = ApplicationPaths.for_desktop(_runtime_profile)
    _database_url = f"sqlite+aiosqlite:///{_desktop_paths.database_file}"
    _vector_db_path = str(_desktop_paths.rag_dir)
    _redis_url = "desktop-sqlite://runtime-state"
else:
    _database_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db"
    )
    _vector_db_path = os.getenv("VECTOR_DB_PATH", "./data/faiss_index")
    _redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class Settings(BaseModel):
    VECTOR_DB_PATH: str = _vector_db_path
    RAG_EMBEDDING_DIM: int = int(os.getenv("RAG_EMBEDDING_DIM", "256"))

    DATABASE_URL: str = normalize_async_database_url(
        _database_url
    )
    REDIS_URL: str = _redis_url

    WORKING_MEMORY_TTL_SECONDS: int = int(os.getenv("WORKING_MEMORY_TTL_SECONDS", "3600"))

    EPISODIC_POST_RETENTION_DAYS: int = int(os.getenv("EPISODIC_POST_RETENTION_DAYS", "365"))
    EPISODIC_THREAD_CONTENT_RETENTION_DAYS: int = int(os.getenv("EPISODIC_THREAD_CONTENT_RETENTION_DAYS", "90"))


settings = Settings()
