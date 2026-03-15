from dynamic_config.models import NacosBackendType, NacosSettings
from dynamic_config.provider import DynamicConfigProvider

ConfigProvider = DynamicConfigProvider

__all__ = ["ConfigProvider", "DynamicConfigProvider", "NacosBackendType", "NacosSettings"]
