from __future__ import annotations

import logging

from dynamic_config.provider import DynamicConfigProvider
from infrastructure.llm.mock_client import ChatMessage
from workflows.common.log_utils import config_metadata, preview_text

logger = logging.getLogger("workflows.demo_summary.summarize")


async def summarize(
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
    prefix = ""
    suffix = ""
    if workflow_config is not None:
        prefix = str(workflow_config.get("prompts.summary_prefix", "") or "")
        suffix = str(workflow_config.get("prompts.summary_suffix", "") or "")
    effective_question = " ".join(part for part in [prefix, question, suffix] if part)
    logger.info(
        "[NODE] workflow=demo_summary session=%s -> summarize:start question=%r profile=%s",
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
    summary = "".join(chunks)
    logger.info(
        "[NODE] workflow=demo_summary session=%s -> summarize:done summary=%r len=%s",
        metadata.get("session_id", "-"),
        preview_text(summary),
        len(summary),
        extra={
            "session_id": metadata.get("session_id", "-"),
            "summary_preview": preview_text(summary),
            "summary_length": len(summary),
        },
    )
    return {"summary": summary}
