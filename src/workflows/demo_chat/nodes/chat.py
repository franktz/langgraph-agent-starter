from __future__ import annotations

import logging
from typing import Any

from dynamic_config.provider import DynamicConfigProvider
from langchain_core.messages import AIMessage, BaseMessage

from infrastructure.llm.context import get_llm_gateway
from infrastructure.llm.gateway import ChatMessage
from workflows.common.llms import resolve_workflow_llm
from workflows.common.log_utils import config_metadata, preview_text

logger = logging.getLogger("workflows.demo-chat.chat")


async def chat(
    state: dict[str, Any],
    *,
    config,
    workflow_config: DynamicConfigProvider | None,
) -> dict[str, Any]:
    metadata = config_metadata(config)
    sys_code = str(state.get("sys_code", "default-system"))
    llm = resolve_workflow_llm(
        workflow_config=workflow_config,
    )
    history = [message for message in state.get("messages", []) if isinstance(message, BaseMessage)]
    upstream_messages = _to_gateway_messages(history)
    system_prompt = ""
    if workflow_config is not None:
        system_prompt = str(workflow_config.get("prompts.system_prompt", "") or "")
    if system_prompt and not any(message.role == "system" for message in upstream_messages):
        upstream_messages.insert(0, ChatMessage(role="system", content=system_prompt))

    last_user = next((message.content for message in reversed(upstream_messages) if message.role == "user"), "")
    logger.info(
        "[NODE] workflow=demo-chat session=%s -> chat:start history=%s llm=%s last_user=%r",
        metadata.get("session_id", "-"),
        len(upstream_messages),
        llm.name,
        preview_text(last_user),
        extra={
            "session_id": metadata.get("session_id", "-"),
            "user_id": metadata.get("user_id"),
            "sys_code": sys_code,
            "llm_name": llm.name,
            "history_messages": len(upstream_messages),
            "question_preview": preview_text(last_user),
        },
    )
    chunks: list[str] = []
    llm_gateway = get_llm_gateway()
    async for token in llm_gateway.stream_chat(
        llm_name=llm.name,
        llm_config=llm.config,
        sys_code=sys_code,
        messages=upstream_messages,
    ):
        chunks.append(token)
    answer = "".join(chunks)
    logger.info(
        "[NODE] workflow=demo-chat session=%s -> chat:done answer=%r len=%s",
        metadata.get("session_id", "-"),
        preview_text(answer),
        len(answer),
        extra={
            "session_id": metadata.get("session_id", "-"),
            "answer_preview": preview_text(answer),
            "answer_length": len(answer),
        },
    )
    return {
        "messages": [AIMessage(content=answer)],
        "answer": answer,
    }


def _to_gateway_messages(messages: list[BaseMessage]) -> list[ChatMessage]:
    converted: list[ChatMessage] = []
    for message in messages:
        role = _role_from_message(message)
        content = _message_text(message)
        if not content:
            continue
        converted.append(
            ChatMessage(
                role=role,
                content=content,
                name=getattr(message, "name", None),
                tool_call_id=getattr(message, "tool_call_id", None),
            )
        )
    return converted


def _role_from_message(message: BaseMessage) -> str:
    message_type = getattr(message, "type", "human")
    if message_type == "ai":
        return "assistant"
    if message_type == "human":
        return "user"
    if message_type == "tool":
        return "tool"
    if message_type == "system":
        return "system"
    return str(message_type)


def _message_text(message: BaseMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)
