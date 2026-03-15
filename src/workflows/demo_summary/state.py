from __future__ import annotations

from typing import TypedDict


class DemoSummaryState(TypedDict, total=False):
    question: str
    systemkey: str
    summary: str
