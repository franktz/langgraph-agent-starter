from __future__ import annotations

import contextvars
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamFrame:
    kind: str
    value: str


StreamWriter = Callable[[StreamFrame], Awaitable[None]]

stream_writer_var: contextvars.ContextVar[StreamWriter | None] = contextvars.ContextVar(
    "stream_writer",
    default=None,
)


@contextmanager
def bind_stream_writer(writer: StreamWriter):
    token = stream_writer_var.set(writer)
    try:
        yield
    finally:
        stream_writer_var.reset(token)


async def emit_stream_token(token: str) -> None:
    writer = stream_writer_var.get()
    if writer is None or not token:
        return
    await writer(StreamFrame(kind="token", value=token))


async def emit_stream_sse(event: str) -> None:
    writer = stream_writer_var.get()
    if writer is None or not event:
        return
    await writer(StreamFrame(kind="sse", value=event))
