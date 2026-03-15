from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.llm.gateway import LlmGateway


llm_gateway_var: contextvars.ContextVar["LlmGateway | None"] = contextvars.ContextVar(
    "llm_gateway",
    default=None,
)


@contextmanager
def bind_llm_gateway(gateway: "LlmGateway"):
    token = llm_gateway_var.set(gateway)
    try:
        yield
    finally:
        llm_gateway_var.reset(token)


def get_llm_gateway() -> "LlmGateway":
    gateway = llm_gateway_var.get()
    if gateway is None:
        raise RuntimeError("llm gateway is not bound to the current workflow execution context")
    return gateway
