from __future__ import annotations

from dynamic_config.provider import DynamicConfigProvider
from infrastructure.llm.mock_client import ChatMessage


async def generate_draft(
    state: dict,
    *,
    config,
    llm_client,
    workflow_config: DynamicConfigProvider | None,
) -> dict[str, str]:
    systemkey = str(state.get("systemkey", "default-system"))
    llm_profile = str(state.get("llm_profile", "default"))
    question = str(state.get("question", ""))
    prompt_prefix = ""
    if workflow_config is not None:
        prompt_prefix = str(workflow_config.get("prompts.draft_prefix", "") or "")
    effective_question = " ".join(part for part in [prompt_prefix, question] if part)
    chunks: list[str] = []
    async for token in llm_client.stream_chat(
        model=llm_profile,
        systemkey=systemkey,
        messages=[ChatMessage(role="user", content=effective_question)],
    ):
        chunks.append(token)
    return {"draft": "".join(chunks)}
