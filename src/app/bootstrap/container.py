from __future__ import annotations

from dataclasses import dataclass

from application.services.chat_completion_service import ChatCompletionService
from application.services.routing_service import RoutingService
from application.services.workflow_catalog_service import WorkflowCatalogService
from infrastructure.config.provider import ConfigProvider
from infrastructure.config.workflow_registry import WorkflowConfigRegistry
from infrastructure.http.client import AsyncHttpClient
from infrastructure.llm.gateway import LlmGateway
from infrastructure.logging.factory import LoggerFactory, setup_bootstrap_logging, setup_logging
from infrastructure.monitoring.langfuse import LangfuseFactory
from infrastructure.persistence.checkpointer import build_checkpointer
from infrastructure.persistence.runtime import WorkflowRuntime
from workflows.registry import WorkflowRegistry


@dataclass
class AppContainer:
    config_provider: ConfigProvider
    logger_factory: LoggerFactory
    http_client: AsyncHttpClient
    workflow_config_registry: WorkflowConfigRegistry
    workflow_registry: WorkflowRegistry
    workflow_catalog: WorkflowCatalogService
    langfuse_factory: LangfuseFactory
    workflow_runtime: WorkflowRuntime
    chat_completion_service: ChatCompletionService


def build_container() -> AppContainer:
    setup_bootstrap_logging()
    config_provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    config_provider.load_from_env()
    logger_factory = setup_logging(config_provider)
    http_client = AsyncHttpClient(logger_factory=logger_factory)
    workflow_config_registry = WorkflowConfigRegistry(
        root_config_provider=config_provider,
        logger_factory=logger_factory,
    )
    workflow_config_registry.refresh_all()
    workflow_registry = WorkflowRegistry(workflow_config_registry=workflow_config_registry)
    workflow_catalog = WorkflowCatalogService(workflow_registry=workflow_registry)
    routing_service = RoutingService(workflow_registry=workflow_registry)
    langfuse_factory = LangfuseFactory(config_provider=config_provider, logger_factory=logger_factory)
    workflow_runtime = WorkflowRuntime(
        config_provider=config_provider,
        logger_factory=logger_factory,
        workflow_registry=workflow_registry,
        checkpointer_builder=build_checkpointer,
        langfuse_factory=langfuse_factory,
        llm_gateway=LlmGateway(
            logger_factory=logger_factory,
            http_client=http_client,
        ),
    )
    chat_completion_service = ChatCompletionService(
        config_provider=config_provider,
        logger_factory=logger_factory,
        workflow_catalog=workflow_catalog,
        routing_service=routing_service,
        workflow_runtime=workflow_runtime,
    )
    return AppContainer(
        config_provider=config_provider,
        logger_factory=logger_factory,
        http_client=http_client,
        workflow_config_registry=workflow_config_registry,
        workflow_registry=workflow_registry,
        workflow_catalog=workflow_catalog,
        langfuse_factory=langfuse_factory,
        workflow_runtime=workflow_runtime,
        chat_completion_service=chat_completion_service,
    )
