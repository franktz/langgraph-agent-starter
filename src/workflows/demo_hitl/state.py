from __future__ import annotations

from typing import TypedDict


class DemoHitlState(TypedDict, total=False):
    question: str
    system_key: str
    llm_profile: str
    draft: str
    final: str
