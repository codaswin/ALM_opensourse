"""Durable SQLite implementation of the Redis surface used by desktop mode."""

from __future__ import annotations

import fnmatch
import sqlite3
import threading
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any


class SQLiteStateClient:
    """Small Redis-compatible client backed by an installation-local SQLite DB."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS state_values (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state_hashes (
                key TEXT NOT NULL,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (key, field)
            );
            CREATE TABLE IF NOT EXISTS state_sorted_sets (
                key TEXT NOT NULL,
                member TEXT NOT NULL,
                score REAL NOT NULL,
                PRIMARY KEY (key, member)
            );
            CREATE TABLE IF NOT EXISTS state_expirations (
                key TEXT PRIMARY KEY,
                expires_at REAL NOT NULL
            );
            """
        )
        self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _purge_if_expired(self, key: str) -> None:
        row = self._connection.execute(
            "SELECT expires_at FROM state_expirations WHERE key = ?", (key,)
        ).fetchone()
        if row is not None and float(row[0]) <= time.time():
            self._delete_unlocked(key)
            self._connection.commit()

    def _delete_unlocked(self, key: str) -> int:
        deleted = 0
        for table in ("state_values", "state_hashes", "state_sorted_sets"):
            cursor = self._connection.execute(f"DELETE FROM {table} WHERE key = ?", (key,))
            deleted += cursor.rowcount
        self._connection.execute("DELETE FROM state_expirations WHERE key = ?", (key,))
        return deleted

    def _key_exists_unlocked(self, key: str) -> bool:
        for table in ("state_values", "state_hashes", "state_sorted_sets"):
            if self._connection.execute(f"SELECT 1 FROM {table} WHERE key = ? LIMIT 1", (key,)).fetchone():
                return True
        return False

    def _set_expiration_unlocked(self, key: str, seconds: int) -> None:
        self._connection.execute(
            "INSERT INTO state_expirations(key, expires_at) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET expires_at = excluded.expires_at",
            (key, time.time() + seconds),
        )

    def get(self, key: str) -> str | None:
        with self._lock:
            self._purge_if_expired(key)
            row = self._connection.execute(
                "SELECT value FROM state_values WHERE key = ?", (key,)
            ).fetchone()
            return str(row[0]) if row is not None else None

    def set(self, key: str, value: Any, *, ex: int | None = None, nx: bool = False) -> bool:
        with self._lock:
            self._purge_if_expired(key)
            if nx and self._key_exists_unlocked(key):
                return False
            self._connection.execute(
                "INSERT INTO state_values(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )
            if ex is None:
                self._connection.execute("DELETE FROM state_expirations WHERE key = ?", (key,))
            else:
                self._set_expiration_unlocked(key, ex)
            self._connection.commit()
            return True

    def delete(self, *keys: str) -> int:
        with self._lock:
            deleted = sum(self._delete_unlocked(key) for key in keys)
            self._connection.commit()
            return deleted

    def incr(self, key: str) -> int:
        return int(self.incrbyfloat(key, 1.0))

    def incrbyfloat(self, key: str, amount: float) -> float:
        with self._lock:
            current = float(self.get(key) or 0.0)
            updated = current + amount
            self.set(key, updated)
            return updated

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            self._purge_if_expired(key)
            if not self._key_exists_unlocked(key):
                return False
            self._set_expiration_unlocked(key, seconds)
            self._connection.commit()
            return True

    def ttl(self, key: str) -> int:
        with self._lock:
            self._purge_if_expired(key)
            row = self._connection.execute(
                "SELECT expires_at FROM state_expirations WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return -1 if self._key_exists_unlocked(key) else -2
            return max(0, int(float(row[0]) - time.time()))

    def hset(
        self,
        key: str,
        field: str | None = None,
        value: Any = None,
        *,
        mapping: Mapping[str, Any] | None = None,
    ) -> int:
        values = dict(mapping or {})
        if field is not None:
            values[field] = value
        with self._lock:
            self._purge_if_expired(key)
            for item_field, item_value in values.items():
                self._connection.execute(
                    "INSERT INTO state_hashes(key, field, value) VALUES (?, ?, ?) "
                    "ON CONFLICT(key, field) DO UPDATE SET value = excluded.value",
                    (key, item_field, str(item_value)),
                )
            self._connection.commit()
            return len(values)

    def hget(self, key: str, field: str) -> str | None:
        with self._lock:
            self._purge_if_expired(key)
            row = self._connection.execute(
                "SELECT value FROM state_hashes WHERE key = ? AND field = ?", (key, field)
            ).fetchone()
            return str(row[0]) if row is not None else None

    def hgetall(self, key: str) -> dict[str, str]:
        with self._lock:
            self._purge_if_expired(key)
            rows = self._connection.execute(
                "SELECT field, value FROM state_hashes WHERE key = ?", (key,)
            ).fetchall()
            return {str(field): str(value) for field, value in rows}

    def hdel(self, key: str, *fields: str) -> int:
        with self._lock:
            before = self._connection.total_changes
            self._connection.executemany(
                "DELETE FROM state_hashes WHERE key = ? AND field = ?",
                [(key, field) for field in fields],
            )
            self._connection.commit()
            return self._connection.total_changes - before

    def zadd(self, key: str, mapping: Mapping[str, float]) -> int:
        with self._lock:
            self._purge_if_expired(key)
            for member, score in mapping.items():
                self._connection.execute(
                    "INSERT INTO state_sorted_sets(key, member, score) VALUES (?, ?, ?) "
                    "ON CONFLICT(key, member) DO UPDATE SET score = excluded.score",
                    (key, member, score),
                )
            self._connection.commit()
            return len(mapping)

    def zrem(self, key: str, *members: str) -> int:
        with self._lock:
            before = self._connection.total_changes
            self._connection.executemany(
                "DELETE FROM state_sorted_sets WHERE key = ? AND member = ?",
                [(key, member) for member in members],
            )
            self._connection.commit()
            return self._connection.total_changes - before

    def zrevrange(self, key: str, start: int, end: int) -> list[str]:
        with self._lock:
            self._purge_if_expired(key)
            rows = self._connection.execute(
                "SELECT member FROM state_sorted_sets WHERE key = ? "
                "ORDER BY score DESC, member DESC LIMIT ? OFFSET ?",
                (key, end - start + 1, start),
            ).fetchall()
            return [str(row[0]) for row in rows]

    def scan_iter(self, *, match: str = "*") -> Iterator[str]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT key FROM state_values UNION SELECT key FROM state_hashes "
                "UNION SELECT key FROM state_sorted_sets"
            ).fetchall()
            keys = [str(row[0]) for row in rows]
        for key in keys:
            with self._lock:
                self._purge_if_expired(key)
                exists = self._key_exists_unlocked(key)
            if exists and fnmatch.fnmatch(key, match):
                yield key

    def pipeline(self) -> SQLiteStatePipeline:
        return SQLiteStatePipeline(self)


class SQLiteStatePipeline:
    def __init__(self, client: SQLiteStateClient) -> None:
        self.client = client
        self._operations: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __enter__(self) -> SQLiteStatePipeline:
        self.client._lock.acquire()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._operations.clear()
        self.client._lock.release()

    def watch(self, *keys: str) -> SQLiteStatePipeline:
        for key in keys:
            self.client._purge_if_expired(key)
        return self

    def unwatch(self) -> None:
        self._operations.clear()

    def multi(self) -> SQLiteStatePipeline:
        return self

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def hset(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("hset", *args, **kwargs)

    def hdel(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("hdel", *args, **kwargs)

    def zadd(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("zadd", *args, **kwargs)

    def zrem(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("zrem", *args, **kwargs)

    def set(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("set", *args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("delete", *args, **kwargs)

    def expire(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("expire", *args, **kwargs)

    def incrbyfloat(self, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        return self._queue("incrbyfloat", *args, **kwargs)

    def execute(self) -> list[Any]:
        results = [getattr(self.client, name)(*args, **kwargs) for name, args, kwargs in self._operations]
        self._operations.clear()
        return results

    def _queue(self, name: str, *args: Any, **kwargs: Any) -> SQLiteStatePipeline:
        self._operations.append((name, args, kwargs))
        return self


class AsyncSQLiteStateClient:
    """Async facade matching the operations used by working memory."""

    def __init__(self, client: SQLiteStateClient) -> None:
        self.client = client

    async def get(self, key: str) -> str | None:
        return self.client.get(key)

    async def set(self, key: str, value: Any, *, ex: int | None = None) -> bool:
        return self.client.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        return self.client.delete(*keys)
