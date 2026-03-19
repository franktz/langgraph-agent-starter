from domain.workflows.errors import MissingWorkflowModelError
from application.services.routing_service import RoutingService
from workflows.registry import WorkflowRegistry


def test_routing_service_resolves_workflow() -> None:
    service = RoutingService(workflow_registry=WorkflowRegistry())

    route = service.resolve(model="demo-summary")

    assert route.workflow == "demo-summary"


def test_routing_service_requires_model() -> None:
    service = RoutingService(workflow_registry=WorkflowRegistry())

    try:
        service.resolve(model=None)
    except MissingWorkflowModelError:
        return
    raise AssertionError("expected missing model to raise")
