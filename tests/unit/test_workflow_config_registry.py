from infrastructure.config.provider import ConfigProvider
from infrastructure.config.provider_cleanup import close_dynamic_config_provider
from infrastructure.config.workflow_registry import WorkflowConfigRegistry
from infrastructure.logging.factory import setup_logging


def test_workflow_config_registry_loads_demo_hitl_config() -> None:
    root_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    root_provider.load_from_env()
    logger_factory = setup_logging(root_provider)
    registry = WorkflowConfigRegistry(
        root_config_provider=root_provider,
        logger_factory=logger_factory,
    )
    try:
        provider = registry.get_provider("demo-hitl")

        assert provider.get("prompts.draft_prefix") == (
            "[Nacos HITL Template] Please produce a release-ready draft before human review."
        )
    finally:
        registry.close()
        close_dynamic_config_provider(root_provider)


def test_workflow_config_registry_propagates_nacos_backend_defaults(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("WORKFLOW_CONFIG_NACOS_ENABLED", "true")
    root_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    root_provider.load_initial(None)
    root_provider._raw["nacos"] = {  # type: ignore[attr-defined]
        "server_addr": "127.0.0.1:8848",
        "group": "DEFAULT_GROUP",
    }
    root_provider._conf = type(root_provider.conf)(root_provider._raw)  # type: ignore[attr-defined]
    logger_factory = setup_logging(root_provider)
    registry = WorkflowConfigRegistry(
        root_config_provider=root_provider,
        logger_factory=logger_factory,
    )
    try:
        item = root_provider.get("workflow_configs.items.demo-summary", {})
        nacos_settings = registry._resolve_nacos_settings(  # type: ignore[attr-defined]
            workflow_name="demo-summary",
            item=item,
        )

        assert nacos_settings is not None
        assert nacos_settings.backend.value == "auto"
        assert nacos_settings.polling_interval_seconds == 2.0
    finally:
        registry.close()
        close_dynamic_config_provider(root_provider)


def test_workflow_config_registry_refresh_all_closes_existing_providers(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    root_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    root_provider.load_from_env()
    logger_factory = setup_logging(root_provider)
    registry = WorkflowConfigRegistry(
        root_config_provider=root_provider,
        logger_factory=logger_factory,
    )
    calls: list[object] = []
    monkeypatch.setattr(
        "infrastructure.config.workflow_registry.close_dynamic_config_provider",
        lambda provider: calls.append(provider),
    )

    registry.refresh_all()
    assert calls == []

    existing = list(registry._providers.values())  # type: ignore[attr-defined]
    registry.refresh_all()

    assert calls == existing
    registry.close()
