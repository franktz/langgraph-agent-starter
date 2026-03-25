from __future__ import annotations

from typing import Any, TypedDict


class DemoHitlState(TypedDict, total=False):
    input_messages: list[dict[str, Any]]
    raw_input_messages: list[dict[str, Any]]
    sys_code: str
    draft: str
    final: str
