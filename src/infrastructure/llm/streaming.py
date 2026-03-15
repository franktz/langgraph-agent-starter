from __future__ import annotations

import contextvars
from collections.abc import Awaitable, Callable
from contextlib import contextmanager

StreamWriter = Callable[[str], Awaitable[None]]

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
    await writer(token)
