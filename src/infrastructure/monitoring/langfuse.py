from __future__ import annotations

from typing import Any

from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import LoggerFactory


class LangfuseFactory:
    def __init__(self, *, config_provider: ConfigProvider, logger_factory: LoggerFactory):
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("infrastructure.monitoring.langfuse")
        self._client: Any | None = None
        self._otel_detach_patched = False

    def _patch_opentelemetry_detach(self) -> None:
        if self._otel_detach_patched:
            return

        try:
            from opentelemetry import context as otel_context_api
            from opentelemetry.context import _RUNTIME_CONTEXT
        except Exception:
            return

        if getattr(otel_context_api, "_langgraph_agent_starter_safe_detach", False):
            self._otel_detach_patched = True
            return

        logger = self._logger

        def _safe_detach(token) -> None:
            try:
                _RUNTIME_CONTEXT.detach(token)
            except ValueError as exc:
                if "different Context" in str(exc):
                    logger.debug("suppressed cross-context opentelemetry detach", exc_info=exc)
                    return
                raise

        otel_context_api.detach = _safe_detach
        otel_context_api._langgraph_agent_starter_safe_detach = True
        self._otel_detach_patched = True

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
            self._patch_opentelemetry_detach()
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
