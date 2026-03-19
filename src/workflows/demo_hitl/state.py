from __future__ import annotations

from typing import TypedDict


class DemoHitlState(TypedDict, total=False):
    question: str
    sys_code: str
    draft: str
    final: str
