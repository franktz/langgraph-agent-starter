from application.services.chat_completion_service import ChatCompletionService
from application.services.routing_service import RoutingService
from application.services.workflow_catalog_service import WorkflowCatalogService
from domain.auth.errors import InvalidSystemKeyError
from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import setup_logging
from presentation.schemas.openai import ChatCompletionRequest
from workflows.registry import WorkflowRegistry


class DummyRuntime:
    async def run_once(self, *, request, ctx):
        return {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}


def test_system_key_is_not_validated_by_default() -> None:
    config_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    config_provider.load_from_env()
    logger_factory = setup_logging(config_provider)
    registry = WorkflowRegistry()
    catalog = WorkflowCatalogService(config_provider=config_provider, workflow_registry=registry)
    routing_service = RoutingService(config_provider=config_provider, workflow_registry=registry)
    service = ChatCompletionService(
        config_provider=config_provider,
        logger_factory=logger_factory,
        workflow_catalog=catalog,
        routing_service=routing_service,
        workflow_runtime=DummyRuntime(),  # type: ignore[arg-type]
    )

    ctx = service.resolve_request_context(
        req=ChatCompletionRequest(model="demo_hitl"),
        systemkey="unknown-system",
        session_id=None,
        user_id=None,
    )
    assert ctx.systemkey == "unknown-system"


def test_system_key_validation_raises_when_enabled() -> None:
    config_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    config_provider.load_initial(
        None
    )
    config_provider._raw["api"]["auth"]["validate_system_key"] = True  # type: ignore[attr-defined]
    config_provider._conf = type(config_provider.conf)(config_provider._raw)  # type: ignore[attr-defined]
    logger_factory = setup_logging(config_provider)
    registry = WorkflowRegistry()
    catalog = WorkflowCatalogService(config_provider=config_provider, workflow_registry=registry)
    routing_service = RoutingService(config_provider=config_provider, workflow_registry=registry)
    service = ChatCompletionService(
        config_provider=config_provider,
        logger_factory=logger_factory,
        workflow_catalog=catalog,
        routing_service=routing_service,
        workflow_runtime=DummyRuntime(),  # type: ignore[arg-type]
    )

    try:
        service.resolve_request_context(
            req=ChatCompletionRequest(model="demo_hitl"),
            systemkey="unknown-system",
            session_id=None,
            user_id=None,
        )
    except InvalidSystemKeyError:
        return
    raise AssertionError("expected invalid system key to raise")
