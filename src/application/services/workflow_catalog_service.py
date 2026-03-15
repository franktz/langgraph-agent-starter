from __future__ import annotations

from workflows.registry import WorkflowRegistry


class WorkflowCatalogService:
    def __init__(self, *, workflow_registry: WorkflowRegistry):
        self._workflow_registry = workflow_registry

    def list_models(self) -> list[dict[str, str]]:
        return [
            {"id": spec.name, "object": "model", "owned_by": "workflow", "description": spec.description}
            for spec in self._workflow_registry.list_specs()
        ]

    def list_model_ids(self) -> list[str]:
        return [spec.name for spec in self._workflow_registry.list_specs()]
