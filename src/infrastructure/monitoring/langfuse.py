from __future__ import annotations

from typing import Any

from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import LoggerFactory


class LangfuseFactory:
    def __init__(self, *, config_provider: ConfigProvider, logger_factory: LoggerFactory):
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("infrastructure.monitoring.langfuse")
        self._client: Any | None = None

    def make_handler(self) -> Any | None:
        if not bool(self._config_provider.get("langfuse.enabled", False)):
            return None
        try:
            from langfuse import Langfuse
            from langfuse.langchain import CallbackHandler
        except Exception:
            return None
        try:
            if self._client is None:
                self._client = Langfuse(
                    public_key=self._config_provider.get("langfuse.public_key"),
                    secret_key=self._config_provider.get("langfuse.secret_key"),
                    host=self._config_provider.get("langfuse.host"),
                )
            return CallbackHandler(public_key=self._config_provider.get("langfuse.public_key"))
        except Exception:
            return None

    def flush(self) -> None:
        if self._client is None:
            return
        try:
            self._client.flush()
        except Exception:
            self._logger.exception("failed to flush langfuse client")
