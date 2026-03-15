from __future__ import annotations

from typing import TypedDict


class DemoSummaryState(TypedDict, total=False):
    question: str
    system_key: str
    llm_profile: str
    summary: str
