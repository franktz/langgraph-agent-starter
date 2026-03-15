from __future__ import annotations

from dataclasses import dataclass

from infrastructure.config.provider import ConfigProvider
from workflows.registry import WorkflowRegistry


@dataclass(frozen=True)
class ResolvedRoute:
    workflow: str
    llm_profile: str


class RoutingService:
    def __init__(self, *, config_provider: ConfigProvider, workflow_registry: WorkflowRegistry):
        self._config_provider = config_provider
        self._workflow_registry = workflow_registry

    def resolve(self, *, model: str | None, system_key: str) -> ResolvedRoute:
        workflow = model or str(self._config_provider.get("api.defaults.workflow", "demo_hitl"))
        valid_workflows = {spec.name for spec in self._workflow_registry.list_specs()}
        if workflow not in valid_workflows:
            raise ValueError(f"unknown workflow model: {workflow}")

        systems = self._config_provider.get("api.auth.systems", [])
        llm_profile = "default"
        if isinstance(systems, list):
            for item in systems:
                if not isinstance(item, dict):
                    continue
                if item.get("key") == system_key:
                    llm_profile = str(item.get("default_llm_profile", "default"))
                    break
        return ResolvedRoute(workflow=workflow, llm_profile=llm_profile)
