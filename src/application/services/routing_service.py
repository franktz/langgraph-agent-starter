from __future__ import annotations

from dataclasses import dataclass

from domain.workflows.errors import MissingWorkflowModelError
from workflows.registry import WorkflowRegistry


@dataclass(frozen=True)
class ResolvedRoute:
    workflow: str


class RoutingService:
    def __init__(self, *, workflow_registry: WorkflowRegistry):
        self._workflow_registry = workflow_registry

    def resolve(self, *, model: str | None) -> ResolvedRoute:
        workflow = str(model or "").strip()
        if not workflow:
            raise MissingWorkflowModelError("missing required field: model")
        valid_workflows = {spec.name for spec in self._workflow_registry.list_specs()}
        if workflow not in valid_workflows:
            raise ValueError(f"unknown workflow model: {workflow}")
        return ResolvedRoute(workflow=workflow)
