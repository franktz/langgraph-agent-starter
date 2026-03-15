from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.config.provider_cleanup import close_dynamic_config_provider


def register_lifespan(app: FastAPI) -> None:
    @asynccontextmanager
    async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
        container = app.state.container
        container.config_provider.load_from_env()
        container.workflow_config_registry.refresh_all()
        await container.workflow_runtime.start()
        try:
            yield
        finally:
            await container.workflow_runtime.stop()
            container.workflow_config_registry.close()
            close_dynamic_config_provider(container.config_provider)
            container.langfuse_factory.flush()
            await container.http_client.aclose()

    app.router.lifespan_context = _lifespan
