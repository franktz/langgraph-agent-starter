from __future__ import annotations

from domain.workflows.spec import WorkflowSpec
from infrastructure.config.workflow_registry import WorkflowConfigRegistry
from workflows.demo_hitl.graph import build as build_demo_hitl
from workflows.demo_summary.graph import build as build_demo_summary


class WorkflowRegistry:
    def __init__(self, *, workflow_config_registry: WorkflowConfigRegistry | None = None) -> None:
        self._workflow_config_registry = workflow_config_registry
        self._specs = {
            "demo_hitl": WorkflowSpec(
                name="demo_hitl",
                description="Draft workflow with human review interrupt",
                supports_hitl=True,
                builder=build_demo_hitl,
            ),
            "demo_summary": WorkflowSpec(
                name="demo_summary",
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
