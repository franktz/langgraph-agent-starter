from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    description: str
    supports_hitl: bool
    builder: Any
    supports_conversation: bool = False
