from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    systemkey: str
    session_id: str
    user_id: str | None
    workflow: str

    @property
    def thread_id(self) -> str:
        user_id = self.user_id or "-"
        return (
            f"workflow={self.workflow}|systemkey={self.systemkey}|"
            f"user_id={user_id}|session_id={self.session_id}"
        )
