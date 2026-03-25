from __future__ import annotations

import logging

from dynamic_config.provider import DynamicConfigProvider
from infrastructure.llm.context import get_llm_gateway
from infrastructure.llm.gateway import ChatMessage
from workflows.common.input_messages import last_text_from_input_messages
from workflows.common.llms import resolve_workflow_llm
from workflows.common.log_utils import config_metadata, preview_text

logger = logging.getLogger("workflows.demo-hitl.generate")


async def generate_draft(
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
    question = last_text_from_input_messages(state.get("input_messages"))
    prompt_prefix = ""
    if workflow_config is not None:
        prompt_prefix = str(workflow_config.get("prompts.draft_prefix", "") or "")
    effective_question = " ".join(part for part in [prompt_prefix, question] if part)
    logger.info(
        "[NODE] workflow=demo-hitl session=%s -> generate_draft:start question=%r llm=%s",
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
    draft = "".join(chunks)
    logger.info(
        "[NODE] workflow=demo-hitl session=%s -> generate_draft:done draft=%r len=%s",
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
