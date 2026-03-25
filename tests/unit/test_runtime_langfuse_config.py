from domain.auth.models import RequestContext
from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import request_id_var, setup_logging
from infrastructure.persistence.runtime import WorkflowRuntime
from workflows.registry import WorkflowRegistry


class DummyLangfuseFactory:
    def make_handler(self):
        return None


class DummyLlmGateway:
    pass


async def _dummy_checkpointer_builder(_config_provider):
    class _Handle:
        saver = None

        async def close(self):
            return None

    return _Handle()


def test_runtime_langfuse_metadata_contains_filterable_fields() -> None:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    logger_factory = setup_logging(provider)
    runtime = WorkflowRuntime(
        config_provider=provider,
        logger_factory=logger_factory,
        workflow_registry=WorkflowRegistry(),
        checkpointer_builder=_dummy_checkpointer_builder,
        langfuse_factory=DummyLangfuseFactory(),
        llm_gateway=DummyLlmGateway(),  # type: ignore[arg-type]
    )
    assert not hasattr(runtime, "_session_state")

    ctx = RequestContext(
        sys_code="full-system-key-demo",
        session_id="session-123",
        user_id="user-456",
        workflow="demo-summary",
    )

    token = request_id_var.set("req-789")
    try:
        config = runtime._config(ctx)
    finally:
        request_id_var.reset(token)
    metadata = config["metadata"]

    assert metadata["request_id"] == "req-789"
    assert metadata["sys_code"] == "full-system-key-demo"
    assert metadata["session_id"] == "session-123"
    assert metadata["user_id"] == "user-456"
    assert metadata["workflow"] == "demo-summary"
    assert metadata["langfuse_request_id"] == "req-789"
    assert metadata["langfuse_session_id"] == "session-123"
    assert metadata["langfuse_user_id"] == "user-456"
    assert config["configurable"]["thread_id"] == (
        "workflow=demo-summary|sys_code=full-system-key-demo|user_id=user-456|session_id=session-123"
    )
    assert "request_id:req-789" in metadata["langfuse_tags"]
    assert "sys_code:full-system-key-demo" in metadata["langfuse_tags"]
    assert "workflow:demo-summary" in metadata["langfuse_tags"]
