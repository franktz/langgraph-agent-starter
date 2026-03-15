from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    systemkey: str
    session_id: str
    user_id: str | None
    workflow: str
    llm_profile: str = "default"
