from __future__ import annotations

import logging

from dynamic_config.provider import DynamicConfigProvider
from infrastructure.llm.context import get_llm_gateway
from infrastructure.llm.gateway import ChatMessage
from workflows.common.llms import resolve_workflow_llm
from workflows.common.log_utils import config_metadata, preview_text

logger = logging.getLogger("workflows.demo-summary.summarize")


async def summarize(
    state: dict,
    *,
    config,
    workflow_config: DynamicConfigProvider | None,
) -> dict[str, str]:
    metadata = config_metadata(config)
    sys_code = str(state.get("sys_code", "default-system"))
    llm = resolve_workflow_llm(
        workflow_config=workflow_config,
    )
    question = str(state.get("question", ""))
    prefix = ""
    suffix = ""
    if workflow_config is not None:
        prefix = str(workflow_config.get("prompts.summary_prefix", "") or "")
        suffix = str(workflow_config.get("prompts.summary_suffix", "") or "")
    effective_question = " ".join(part for part in [prefix, question, suffix] if part)
    logger.info(
        "[NODE] workflow=demo-summary session=%s -> summarize:start question=%r llm=%s",
        metadata.get("session_id", "-"),
        preview_text(question),
        llm.name,
        extra={
            "session_id": metadata.get("session_id", "-"),
            "user_id": metadata.get("user_id"),
            "sys_code": sys_code,
            "llm_name": llm.name,
            "question_preview": preview_text(question),
        },
    )
    chunks: list[str] = []
    llm_gateway = get_llm_gateway()
    async for token in llm_gateway.stream_chat(
        llm_name=llm.name,
        llm_config=llm.config,
        sys_code=sys_code,
        messages=[ChatMessage(role="user", content=effective_question)],
    ):
        chunks.append(token)
    summary = "".join(chunks)
    logger.info(
        "[NODE] workflow=demo-summary session=%s -> summarize:done summary=%r len=%s",
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
