from __future__ import annotations

import logging

from dynamic_config.provider import DynamicConfigProvider
from infrastructure.llm.mock_client import ChatMessage
from workflows.common.log_utils import config_metadata, preview_text

logger = logging.getLogger("workflows.demo_hitl.generate")


async def generate_draft(
    state: dict,
    *,
    config,
    llm_client,
    workflow_config: DynamicConfigProvider | None,
) -> dict[str, str]:
    metadata = config_metadata(config)
    systemkey = str(state.get("systemkey", "default-system"))
    llm_profile = str(state.get("llm_profile", "default"))
    question = str(state.get("question", ""))
    prompt_prefix = ""
    if workflow_config is not None:
        prompt_prefix = str(workflow_config.get("prompts.draft_prefix", "") or "")
    effective_question = " ".join(part for part in [prompt_prefix, question] if part)
    logger.info(
        "[NODE] workflow=demo_hitl session=%s -> generate_draft:start question=%r profile=%s",
        metadata.get("session_id", "-"),
        preview_text(question),
        llm_profile,
        extra={
            "session_id": metadata.get("session_id", "-"),
            "user_id": metadata.get("user_id"),
            "systemkey": systemkey,
            "llm_profile": llm_profile,
            "question_preview": preview_text(question),
        },
    )
    chunks: list[str] = []
    async for token in llm_client.stream_chat(
        model=llm_profile,
        systemkey=systemkey,
        messages=[ChatMessage(role="user", content=effective_question)],
    ):
        chunks.append(token)
    draft = "".join(chunks)
    logger.info(
        "[NODE] workflow=demo_hitl session=%s -> generate_draft:done draft=%r len=%s",
        metadata.get("session_id", "-"),
        preview_text(draft),
        len(draft),
        extra={
            "session_id": metadata.get("session_id", "-"),
            "draft_preview": preview_text(draft),
            "draft_length": len(draft),
        },
    )
    return {"draft": draft}
