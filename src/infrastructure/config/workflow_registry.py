from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from dynamic_config.models import NacosBackendType, NacosSettings
from dynamic_config.provider import DynamicConfigProvider
from infrastructure.config.provider import ConfigProvider
from infrastructure.config.provider_cleanup import close_dynamic_config_provider
from infrastructure.logging.factory import LoggerFactory


class WorkflowConfigRegistry:
    def __init__(
        self,
        *,
        root_config_provider: ConfigProvider,
        logger_factory: LoggerFactory,
        root_path: str = ".",
    ) -> None:
        self._root_config_provider = root_config_provider
        self._logger = logger_factory.get_logger("infrastructure.workflow_config")
        self._root_path = Path(root_path)
        self._providers: dict[str, DynamicConfigProvider] = {}

    def refresh_all(self) -> None:
        self.close()
        items = self._workflow_items()
        for workflow_name in items:
            self._providers[workflow_name] = self._build_provider(workflow_name)

    def get_provider(self, workflow_name: str) -> DynamicConfigProvider:
        provider = self._providers.get(workflow_name)
        if provider is not None:
            return provider
        provider = self._build_provider(workflow_name)
        self._providers[workflow_name] = provider
        return provider

    def close(self) -> None:
        for provider in self._providers.values():
            close_dynamic_config_provider(provider)
        self._providers.clear()

    def _build_provider(self, workflow_name: str) -> DynamicConfigProvider:
        item = self._workflow_items().get(workflow_name, {})
        if not isinstance(item, Mapping):
            item = {}
        local_path = self._resolve_local_path(workflow_name=workflow_name, item=item)
        provider = DynamicConfigProvider(local_yaml_path=str(local_path))
        nacos_settings = self._resolve_nacos_settings(workflow_name=workflow_name, item=item)
        provider.load_initial(nacos_settings)
        self._logger.info(
            "workflow config provider ready",
            extra={
                "workflow": workflow_name,
                "local_path": str(local_path),
                "nacos_data_id": nacos_settings.data_id if nacos_settings else None,
            },
        )
        return provider

    def _workflow_items(self) -> dict[str, Any]:
        items = self._root_config_provider.get("workflow_configs.items", {})
        return items if isinstance(items, dict) else {}

    def _resolve_local_path(self, *, workflow_name: str, item: Mapping[str, Any]) -> Path:
        local_path = item.get("local_path")
        if isinstance(local_path, str) and local_path:
            return self._root_path / local_path
        defaults_dir = self._root_config_provider.get("workflow_configs.defaults.local_dir", "configs/workflows")
        return self._root_path / str(defaults_dir) / f"{workflow_name}.yaml"

    def _resolve_nacos_settings(
        self,
        *,
        workflow_name: str,
        item: Mapping[str, Any],
    ) -> NacosSettings | None:
        item_nacos = item.get("nacos", {})
        if not isinstance(item_nacos, Mapping):
            item_nacos = {}
        default_nacos = self._root_config_provider.get("workflow_configs.defaults.nacos", {})
        if not isinstance(default_nacos, Mapping):
            default_nacos = {}
        root_nacos = self._root_config_provider.get("nacos", {})
        if not isinstance(root_nacos, Mapping):
            root_nacos = {}
        base_nacos = self._root_config_provider.nacos_settings

        forced_enabled = os.getenv("WORKFLOW_CONFIG_NACOS_ENABLED")
        if forced_enabled is not None and forced_enabled.strip().lower() in {"0", "false", "no", "off"}:
            return None

        enabled = item_nacos.get("enabled", default_nacos.get("enabled", True))
        if not enabled:
            return None

        server_addr = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "server_addr")
        if not server_addr:
            return None

        data_id = item_nacos.get("data_id")
        if not data_id:
            template = default_nacos.get("data_id_template")
            if isinstance(template, str) and template:
                data_id = template.format(workflow=workflow_name)
        if not data_id:
            data_id = f"{workflow_name}.yaml"

        group = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "group") or "DEFAULT_GROUP"
        namespace = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "namespace")
        username = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "username")
        password = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "password")
        backend = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "backend")
        polling_interval_seconds = self._pick(
            item_nacos,
            default_nacos,
            root_nacos,
            base_nacos,
            "polling_interval_seconds",
        )
        sdk_log_path = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "sdk_log_path")
        sdk_log_level = self._pick(item_nacos, default_nacos, root_nacos, base_nacos, "sdk_log_level")
        return NacosSettings(
            server_addr=str(server_addr),
            namespace=str(namespace) if namespace is not None else None,
            data_id=str(data_id),
            group=str(group),
            username=str(username) if username is not None else None,
            password=str(password) if password is not None else None,
            backend=self._parse_backend(backend),
            polling_interval_seconds=self._parse_polling_interval(polling_interval_seconds),
            sdk_log_path=str(sdk_log_path) if sdk_log_path is not None else None,
            sdk_log_level=sdk_log_level,
        )

    def _pick(
        self,
        item_nacos: Mapping[str, Any],
        default_nacos: Mapping[str, Any],
        root_nacos: Mapping[str, Any],
        base_nacos: NacosSettings | None,
        field: str,
    ) -> Any:
        if field in item_nacos and item_nacos.get(field) is not None:
            return item_nacos.get(field)
        if field in default_nacos and default_nacos.get(field) is not None:
            return default_nacos.get(field)
        if field in root_nacos and root_nacos.get(field) is not None:
            return root_nacos.get(field)
        if base_nacos is not None:
            return getattr(base_nacos, field, None)
        return None

    @staticmethod
    def _parse_backend(value: Any) -> NacosBackendType:
        if isinstance(value, NacosBackendType):
            return value
        if isinstance(value, str):
            try:
                return NacosBackendType(value.strip().lower())
            except ValueError:
                return NacosBackendType.AUTO
        return NacosBackendType.AUTO

    @staticmethod
    def _parse_polling_interval(value: Any) -> float:
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
        if isinstance(value, str):
            try:
                parsed = float(value)
            except ValueError:
                return 2.0
            return parsed if parsed > 0 else 2.0
        return 2.0
