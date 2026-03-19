from __future__ import annotations

from domain.workflows.spec import WorkflowSpec
from infrastructure.config.workflow_registry import WorkflowConfigRegistry
from workflows.demo_chat.graph import build as build_demo_chat
from workflows.demo_hitl.graph import build as build_demo_hitl
from workflows.demo_summary.graph import build as build_demo_summary


class WorkflowRegistry:
    def __init__(self, *, workflow_config_registry: WorkflowConfigRegistry | None = None) -> None:
        self._workflow_config_registry = workflow_config_registry
        self._specs = {
            "demo-chat": WorkflowSpec(
                name="demo-chat",
                description="Multi-turn chat workflow backed by LangGraph state",
                supports_hitl=False,
                supports_conversation=True,
                builder=build_demo_chat,
            ),
            "demo-hitl": WorkflowSpec(
                name="demo-hitl",
                description="Draft workflow with human review interrupt",
                supports_hitl=True,
                builder=build_demo_hitl,
            ),
            "demo-summary": WorkflowSpec(
                name="demo-summary",
                description="Summary workflow without interrupt",
                supports_hitl=False,
                builder=build_demo_summary,
            ),
        }

    def build(self, name: str, *, checkpointer=None):
        spec = self._specs[name]
        workflow_config = None
        if self._workflow_config_registry is not None:
            workflow_config = self._workflow_config_registry.get_provider(name)
        return spec.builder(
            checkpointer=checkpointer,
            workflow_config=workflow_config,
        )

    def list_specs(self) -> list[WorkflowSpec]:
        return [self._specs[name] for name in sorted(self._specs)]

    def get_spec(self, name: str) -> WorkflowSpec:
        return self._specs[name]
