from __future__ import annotations

import sys
from types import ModuleType

import pytest

from infrastructure.config.provider import ConfigProvider
from infrastructure.persistence.checkpointer import build_checkpointer


def _build_provider(raw: dict) -> ConfigProvider:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_initial(None)
    provider._raw = raw  # type: ignore[attr-defined]
    provider._conf = type(provider.conf)(raw)  # type: ignore[attr-defined]
    return provider


@pytest.mark.asyncio
async def test_build_checkpointer_returns_none_when_backend_is_null() -> None:
    provider = _build_provider({"langgraph": {"checkpointer": {"backend": None}}})

    handle = await build_checkpointer(provider)

    assert handle is None


@pytest.mark.asyncio
async def test_build_checkpointer_returns_memory_saver() -> None:
    provider = _build_provider({"langgraph": {"checkpointer": {"backend": "memory"}}})

    handle = await build_checkpointer(provider)

    assert handle is not None
    assert type(handle.saver).__name__.endswith("MemorySaver")
    await handle.close()


@pytest.mark.asyncio
async def test_build_checkpointer_uses_grouped_redis_config(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    class _Manager:
        async def __aenter__(self):
            captured["entered"] = True
            return "redis-saver"

        async def __aexit__(self, *_args):
            captured["closed"] = True

    class _AsyncRedisSaver:
        @staticmethod
        def from_conn_string(url, **kwargs):  # type: ignore[no-untyped-def]
            captured["url"] = url
            captured["kwargs"] = kwargs
            return _Manager()

    redis_module = ModuleType("langgraph.checkpoint.redis")
    redis_module.AsyncRedisSaver = _AsyncRedisSaver
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.redis", redis_module)

    provider = _build_provider(
        {
            "langgraph": {
                "checkpointer": {
                    "backend": "redis",
                    "redis": {
                        "url": "redis://127.0.0.1:6379/0",
                        "cluster_mode": True,
                    },
                }
            }
        }
    )

    handle = await build_checkpointer(provider)

    assert handle is not None
    assert handle.saver == "redis-saver"
    assert captured["url"] == "redis://127.0.0.1:6379/0"
    assert captured["kwargs"] == {"connection_args": {"cluster": True}}
    await handle.close()
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_build_checkpointer_supports_legacy_redis_url(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    class _Manager:
        async def __aenter__(self):
            return "redis-saver"

        async def __aexit__(self, *_args):
            captured["closed"] = True

    class _AsyncRedisSaver:
        @staticmethod
        def from_conn_string(url, **kwargs):  # type: ignore[no-untyped-def]
            captured["url"] = url
            captured["kwargs"] = kwargs
            return _Manager()

    redis_module = ModuleType("langgraph.checkpoint.redis")
    redis_module.AsyncRedisSaver = _AsyncRedisSaver
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.redis", redis_module)

    provider = _build_provider(
        {
            "langgraph": {
                "checkpointer": {
                    "backend": "redis",
                    "redis_url": "redis://legacy:6379/0",
                }
            }
        }
    )

    handle = await build_checkpointer(provider)

    assert handle is not None
    assert captured["url"] == "redis://legacy:6379/0"
    assert captured["kwargs"] == {"connection_args": None}
    await handle.close()


@pytest.mark.asyncio
async def test_build_checkpointer_uses_mysql_config(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    class _Saver:
        async def setup(self) -> None:
            captured["setup_called"] = True

    class _Manager:
        async def __aenter__(self):
            captured["entered"] = True
            return _Saver()

        async def __aexit__(self, *_args):
            captured["closed"] = True

    class _AIOMySQLSaver:
        @staticmethod
        def from_conn_string(conn_string):  # type: ignore[no-untyped-def]
            captured["conn_string"] = conn_string
            return _Manager()

    mysql_aio_module = ModuleType("langgraph.checkpoint.mysql.aio")
    mysql_aio_module.AIOMySQLSaver = _AIOMySQLSaver
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.mysql.aio", mysql_aio_module)

    provider = _build_provider(
        {
            "langgraph": {
                "checkpointer": {
                    "backend": "mysql",
                    "mysql": {"conn_string": "mysql+aiomysql://user:pass@localhost:3306/demo"},
                }
            }
        }
    )

    handle = await build_checkpointer(provider)

    assert handle is not None
    assert captured["conn_string"] == "mysql+aiomysql://user:pass@localhost:3306/demo"
    assert captured["setup_called"] is True
    await handle.close()
    assert captured["closed"] is True


@pytest.mark.asyncio
async def test_build_checkpointer_uses_mongodb_config(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    class _Manager:
        def __enter__(self):
            captured["entered"] = True
            return "mongodb-saver"

        def __exit__(self, *_args):
            captured["closed"] = True

    class _MongoDBSaver:
        @staticmethod
        def from_conn_string(conn_string, **kwargs):  # type: ignore[no-untyped-def]
            captured["conn_string"] = conn_string
            captured["kwargs"] = kwargs
            return _Manager()

    mongodb_module = ModuleType("langgraph.checkpoint.mongodb")
    mongodb_module.MongoDBSaver = _MongoDBSaver
    monkeypatch.setitem(sys.modules, "langgraph.checkpoint.mongodb", mongodb_module)

    provider = _build_provider(
        {
            "langgraph": {
                "checkpointer": {
                    "backend": "mongodb",
                    "mongodb": {
                        "conn_string": "mongodb://127.0.0.1:27017",
                        "db_name": "langgraph_checkpoint",
                        "checkpoint_collection_name": "checkpoints",
                        "writes_collection_name": "checkpoint_writes",
                        "ttl": "300",
                    },
                }
            }
        }
    )

    handle = await build_checkpointer(provider)

    assert handle is not None
    assert handle.saver == "mongodb-saver"
    assert captured["conn_string"] == "mongodb://127.0.0.1:27017"
    assert captured["kwargs"] == {
        "db_name": "langgraph_checkpoint",
        "checkpoint_collection_name": "checkpoints",
        "writes_collection_name": "checkpoint_writes",
        "ttl": 300,
    }
    await handle.close()
    assert captured["closed"] is True
