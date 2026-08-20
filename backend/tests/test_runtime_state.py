from __future__ import annotations

import time
from pathlib import Path

from app.runtime_state import SQLiteStateClient


def test_sqlite_state_survives_client_restart(tmp_path: Path) -> None:
    path = tmp_path / "runtime.sqlite3"
    first = SQLiteStateClient(path)
    first.set("safety:kill-switch", "paused")
    first.close()

    second = SQLiteStateClient(path)
    try:
        assert second.get("safety:kill-switch") == "paused"
    finally:
        second.close()


def test_sqlite_state_supports_atomic_counter_pipeline_and_ttl(tmp_path: Path) -> None:
    client = SQLiteStateClient(tmp_path / "runtime.sqlite3")
    try:
        with client.pipeline() as pipeline:
            pipeline.incrbyfloat("cost", 1.25)
            pipeline.expire("cost", 60)
            assert pipeline.execute() == [1.25, True]
        assert client.get("cost") == "1.25"
        assert client.ttl("cost") > 0
    finally:
        client.close()


def test_sqlite_state_expiry_and_set_nx(tmp_path: Path) -> None:
    client = SQLiteStateClient(tmp_path / "runtime.sqlite3")
    try:
        assert client.set("lease", "owner-a", nx=True, ex=1) is True
        assert client.set("lease", "owner-b", nx=True, ex=1) is False
        assert client.get("lease") == "owner-a"
        client._connection.execute(
            "UPDATE state_expirations SET expires_at = ? WHERE key = ?",
            (time.time() - 1, "lease"),
        )
        client._connection.commit()
        assert client.get("lease") is None
        assert client.set("lease", "owner-b", nx=True) is True
    finally:
        client.close()


def test_sqlite_state_hash_and_sorted_set_operations(tmp_path: Path) -> None:
    client = SQLiteStateClient(tmp_path / "runtime.sqlite3")
    try:
        with client.pipeline() as pipeline:
            pipeline.hset("activity", "one", "first")
            pipeline.hset("activity", "two", "second")
            pipeline.zadd("order", {"one": 1.0, "two": 2.0})
            pipeline.execute()
        assert client.hgetall("activity") == {"one": "first", "two": "second"}
        assert client.zrevrange("order", 0, 0) == ["two"]
        assert sorted(client.scan_iter(match="act*")) == ["activity"]
        assert client.hdel("activity", "one") == 1
        assert client.zrem("order", "one") == 1
    finally:
        client.close()
