from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/health/details")
async def health_details(request: Request) -> dict[str, object]:
    container = request.app.state.container
    return {
        "ok": True,
        "default_workflow": container.workflow_catalog.default_workflow(),
        "workflows": container.workflow_catalog.list_model_ids(),
        "system_key_validation": container.config_provider.get("api.auth.validate_system_key", False),
    }
