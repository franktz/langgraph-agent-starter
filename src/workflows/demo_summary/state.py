from __future__ import annotations

from typing import Any, TypedDict


class DemoSummaryState(TypedDict, total=False):
    input_messages: list[dict[str, Any]]
    raw_input_messages: list[dict[str, Any]]
    sys_code: str
    summary: str
