from application.services.routing_service import RoutingService
from infrastructure.config.provider import ConfigProvider
from workflows.registry import WorkflowRegistry


def test_routing_service_resolves_workflow_and_llm_profile() -> None:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    service = RoutingService(config_provider=provider, workflow_registry=WorkflowRegistry())

    route = service.resolve(model="demo_summary", systemkey="demo-system")

    assert route.workflow == "demo_summary"
    assert route.llm_profile == "default"
