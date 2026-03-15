from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dynamic_config.provider import DynamicConfigProvider


@dataclass(frozen=True)
class WorkflowLlm:
    name: str
    config: dict[str, Any]


def _local_fallback_provider(
    workflow_config: DynamicConfigProvider,
) -> DynamicConfigProvider | None:
    try:
        provider = DynamicConfigProvider(local_yaml_path=str(workflow_config.local_yaml_path))
        provider.load_initial(None)
    except Exception:
        return None
    return provider


def resolve_workflow_llm(
    *,
    workflow_config: DynamicConfigProvider | None,
) -> WorkflowLlm:
    if workflow_config is None:
        raise ValueError("workflow config is required to resolve llm")

    provider = workflow_config
    final_name = "default"

    llm_config = provider.get(f"llm.{final_name}")
    if not isinstance(llm_config, Mapping) and provider is workflow_config:
        fallback_provider = _local_fallback_provider(workflow_config)
        if fallback_provider is not None:
            provider = fallback_provider
            llm_config = provider.get(f"llm.{final_name}")
    if not isinstance(llm_config, Mapping):
        raise ValueError(f"workflow llm '{final_name}' not found")
    return WorkflowLlm(name=final_name, config=dict(llm_config))
