from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import setup_logging
from infrastructure.monitoring.langfuse import LangfuseFactory


def test_langfuse_factory_patches_cross_context_detach(monkeypatch) -> None:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    logger_factory = setup_logging(provider)
    factory = LangfuseFactory(config_provider=provider, logger_factory=logger_factory)

    from opentelemetry import context as otel_context_api

    class DummyRuntimeContext:
        def detach(self, _token) -> None:
            raise ValueError("Token was created in a different Context")

    monkeypatch.setattr(
        "opentelemetry.context._RUNTIME_CONTEXT",
        DummyRuntimeContext(),
        raising=False,
    )
    monkeypatch.setattr(
        otel_context_api,
        "_langgraph_agent_starter_safe_detach",
        False,
        raising=False,
    )

    factory._patch_opentelemetry_detach()

    otel_context_api.detach(object())
