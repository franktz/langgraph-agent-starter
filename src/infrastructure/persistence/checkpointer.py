from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from infrastructure.config.provider import ConfigProvider


@dataclass(frozen=True)
class CheckpointerHandle:
    saver: Any
    close: Callable[[], Awaitable[None]]


async def build_checkpointer(config_provider: ConfigProvider) -> CheckpointerHandle | None:
    backend = _normalize_backend(config_provider.get("langgraph.checkpointer.backend"))
    if backend is None:
        return None
    if backend == "memory":
        return _build_memory_checkpointer()
    if backend == "redis":
        return await _build_redis_checkpointer(config_provider)
    if backend == "mysql":
        return await _build_mysql_checkpointer(config_provider)
    if backend == "mongodb":
        return _build_mongodb_checkpointer(config_provider)
    raise ValueError(f"Unsupported langgraph.checkpointer.backend: {backend}")


def _build_memory_checkpointer() -> CheckpointerHandle:
    from langgraph.checkpoint.memory import MemorySaver

    saver = MemorySaver()

    async def _close() -> None:
        return None

    return CheckpointerHandle(saver=saver, close=_close)


async def _build_redis_checkpointer(config_provider: ConfigProvider) -> CheckpointerHandle:
    from langgraph.checkpoint.redis import AsyncRedisSaver

    redis_url = _require_string(
        config_provider,
        "langgraph.checkpointer.redis.url",
        legacy_path="langgraph.checkpointer.redis_url",
    )
    cluster_mode = _optional_bool(config_provider.get("langgraph.checkpointer.redis.cluster_mode"))
    connection_args = {"cluster": cluster_mode} if cluster_mode is not None else None
    manager = AsyncRedisSaver.from_conn_string(redis_url, connection_args=connection_args)
    saver = await manager.__aenter__()

    async def _close() -> None:
        await manager.__aexit__(None, None, None)

    return CheckpointerHandle(saver=saver, close=_close)


async def _build_mysql_checkpointer(config_provider: ConfigProvider) -> CheckpointerHandle:
    from langgraph.checkpoint.mysql.aio import AIOMySQLSaver

    conn_string = _require_string(config_provider, "langgraph.checkpointer.mysql.conn_string")
    manager = AIOMySQLSaver.from_conn_string(conn_string)
    saver = await manager.__aenter__()
    await saver.setup()

    async def _close() -> None:
        await manager.__aexit__(None, None, None)

    return CheckpointerHandle(saver=saver, close=_close)


def _build_mongodb_checkpointer(config_provider: ConfigProvider) -> CheckpointerHandle:
    from langgraph.checkpoint.mongodb import MongoDBSaver

    conn_string = _require_string(config_provider, "langgraph.checkpointer.mongodb.conn_string")
    db_name = _require_string(config_provider, "langgraph.checkpointer.mongodb.db_name")
    checkpoint_collection_name = _string_or_default(
        config_provider.get("langgraph.checkpointer.mongodb.checkpoint_collection_name"),
        "checkpoints",
    )
    writes_collection_name = _string_or_default(
        config_provider.get("langgraph.checkpointer.mongodb.writes_collection_name"),
        "checkpoint_writes",
    )
    ttl = _optional_int(config_provider.get("langgraph.checkpointer.mongodb.ttl"))
    manager = MongoDBSaver.from_conn_string(
        conn_string,
        db_name=db_name,
        checkpoint_collection_name=checkpoint_collection_name,
        writes_collection_name=writes_collection_name,
        ttl=ttl,
    )
    saver = manager.__enter__()

    async def _close() -> None:
        manager.__exit__(None, None, None)

    return CheckpointerHandle(saver=saver, close=_close)


def _normalize_backend(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"", "none", "null"}:
        return None
    return normalized


def _require_string(
    config_provider: ConfigProvider,
    path: str,
    *,
    legacy_path: str | None = None,
) -> str:
    value = config_provider.get(path)
    if value is None and legacy_path is not None:
        value = config_provider.get(legacy_path)
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    raise ValueError(f"Missing required checkpointer config: {path}")


def _string_or_default(value: Any, default: str) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return default


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        return int(normalized)
    raise ValueError(f"Expected integer-compatible value, got {type(value).__name__}")
