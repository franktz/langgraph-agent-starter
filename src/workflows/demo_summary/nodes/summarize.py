from __future__ import annotations

from dynamic_config.provider import DynamicConfigProvider
from infrastructure.llm.mock_client import ChatMessage


async def summarize(
    state: dict,
    *,
    config,
    llm_client,
    workflow_config: DynamicConfigProvider | None,
) -> dict[str, str]:
    systemkey = str(state.get("systemkey", "default-system"))
    llm_profile = str(state.get("llm_profile", "default"))
    question = str(state.get("question", ""))
    prefix = ""
    suffix = ""
    if workflow_config is not None:
        prefix = str(workflow_config.get("prompts.summary_prefix", "") or "")
        suffix = str(workflow_config.get("prompts.summary_suffix", "") or "")
    effective_question = " ".join(part for part in [prefix, question, suffix] if part)
    chunks: list[str] = []
    async for token in llm_client.stream_chat(
        model=llm_profile,
        systemkey=systemkey,
        messages=[ChatMessage(role="user", content=effective_question)],
    ):
        chunks.append(token)
    return {"summary": "".join(chunks)}
