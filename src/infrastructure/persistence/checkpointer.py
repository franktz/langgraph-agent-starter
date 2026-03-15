from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from infrastructure.config.provider import ConfigProvider


@dataclass(frozen=True)
class CheckpointerHandle:
    saver: Any
    close: Any


async def build_checkpointer(config_provider: ConfigProvider) -> CheckpointerHandle:
    backend = str(config_provider.get("langgraph.checkpointer.backend", "memory"))
    if backend == "redis":
        from langgraph.checkpoint.redis import AsyncRedisSaver

        manager = AsyncRedisSaver.from_conn_string(str(config_provider.get("langgraph.checkpointer.redis_url")))
        saver = await manager.__aenter__()

        async def _close() -> None:
            await manager.__aexit__(None, None, None)

        return CheckpointerHandle(saver=saver, close=_close)

    from langgraph.checkpoint.memory import MemorySaver

    saver = MemorySaver()

    async def _close() -> None:
        return None

    return CheckpointerHandle(saver=saver, close=_close)
