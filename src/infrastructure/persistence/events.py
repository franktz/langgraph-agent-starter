from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeEvent:
    type: str
    payload: dict[str, Any]

    def to_chunk(
        self, *, completion_id: str, created: int, workflow: str, session_id: str, user_id: str | None
    ) -> dict[str, Any]:
        return {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": workflow,
            "choices": [
                {
                    "index": 0,
                    "delta": self.payload,
                    "finish_reason": None,
                }
            ],
            "session_id": session_id,
            "user_id": user_id,
        }
