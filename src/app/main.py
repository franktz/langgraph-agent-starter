from __future__ import annotations

from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.api.routers.openai import router as openai_router
from app.bootstrap.container import build_container
from app.bootstrap.lifespan import register_lifespan


def create_app() -> FastAPI:
    app = FastAPI(title="langgraph-agent-starter")
    container = build_container()
    app.state.container = container
    register_lifespan(app)
    app.include_router(health_router)
    app.include_router(openai_router)
    return app


app = create_app()
