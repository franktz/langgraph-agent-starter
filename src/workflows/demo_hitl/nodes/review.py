from __future__ import annotations

from langgraph.types import interrupt


async def human_review(state: dict, *, config) -> dict[str, str]:
    payload = interrupt({"draft": state.get("draft")})
    final = payload.get("final") if isinstance(payload, dict) else None
    return {"final": str(final or state.get("draft") or "")}
