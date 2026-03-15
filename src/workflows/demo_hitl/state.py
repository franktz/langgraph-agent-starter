from __future__ import annotations

from typing import TypedDict


class DemoHitlState(TypedDict, total=False):
    question: str
    systemkey: str
    draft: str
    final: str
