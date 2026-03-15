from dynamic_config import NacosSettings
from infrastructure.config.provider import ConfigProvider
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

    provider = registry.get_provider("demo_hitl")

    assert provider.get("prompts.draft_prefix") == (
        "[Nacos HITL Template] Please produce a release-ready draft before human review."
    )


def test_workflow_config_registry_propagates_nacos_backend_defaults() -> None:
    root_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    root_provider.load_initial(
        NacosSettings(
            server_addr="127.0.0.1:8848",
            namespace=None,
            data_id="langgraph-agent-starter.yaml",
            group="DEFAULT_GROUP",
        )
    )
    logger_factory = setup_logging(root_provider)
    registry = WorkflowConfigRegistry(
        root_config_provider=root_provider,
        logger_factory=logger_factory,
    )

    provider = registry.get_provider("demo_summary")

    assert provider.nacos_settings is not None
    assert provider.nacos_settings.backend.value == "auto"
    assert provider.nacos_settings.polling_interval_seconds == 2.0
