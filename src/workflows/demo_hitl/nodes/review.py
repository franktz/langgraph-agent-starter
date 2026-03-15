from __future__ import annotations

import logging

from langgraph.types import interrupt
from workflows.common.log_utils import config_metadata, preview_text

logger = logging.getLogger("workflows.demo_hitl.review")


async def human_review(state: dict, *, config) -> dict[str, str]:
    metadata = config_metadata(config)
    draft = str(state.get("draft") or "")
    logger.info(
        "[HITL] workflow=demo_hitl session=%s -> human_review:wait draft=%r len=%s",
        metadata.get("session_id", "-"),
        preview_text(draft),
        len(draft),
        extra={
            "session_id": metadata.get("session_id", "-"),
            "draft_preview": preview_text(draft),
            "draft_length": len(draft),
        },
    )
    payload = interrupt({"draft": state.get("draft")})
    final = payload.get("final") if isinstance(payload, dict) else None
    final_text = str(final or state.get("draft") or "")
    logger.info(
        "[HITL] workflow=demo_hitl session=%s -> human_review:resume final=%r len=%s",
        metadata.get("session_id", "-"),
        preview_text(final_text),
        len(final_text),
        extra={
            "session_id": metadata.get("session_id", "-"),
            "final_preview": preview_text(final_text),
            "final_length": len(final_text),
        },
    )
    return {"final": final_text}
