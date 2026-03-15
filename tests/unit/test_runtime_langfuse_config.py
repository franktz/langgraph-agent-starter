from domain.auth.models import RequestContext
from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import setup_logging
from infrastructure.persistence.runtime import WorkflowRuntime
from workflows.registry import WorkflowRegistry


class DummyLangfuseFactory:
    def make_handler(self):
        return None


class DummyLlmClient:
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
        llm_client=DummyLlmClient(),  # type: ignore[arg-type]
    )

    ctx = RequestContext(
        systemkey="full-system-key-demo",
        session_id="session-123",
        user_id="user-456",
        workflow="demo_summary",
        llm_profile="default",
    )

    config = runtime._config(ctx)
    metadata = config["metadata"]

    assert metadata["systemkey"] == "full-system-key-demo"
    assert metadata["session_id"] == "session-123"
    assert metadata["user_id"] == "user-456"
    assert metadata["langfuse_session_id"] == "session-123"
    assert metadata["langfuse_user_id"] == "user-456"
    assert "systemkey:full-system-key-demo" in metadata["langfuse_tags"]
