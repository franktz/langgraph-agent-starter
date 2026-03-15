from __future__ import annotations

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from domain.auth.errors import InvalidSystemKeyError
from infrastructure.http.errors import HttpClientResponseError, HttpClientTimeoutError
from presentation.schemas.openai import ChatCompletionRequest

router = APIRouter()


@router.get("/v1/models")
async def list_models(request: Request) -> dict[str, object]:
    service = request.app.state.container.workflow_catalog
    return {"object": "list", "data": service.list_models()}


@router.post("/v1/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    systemkey: str | None = Header(default=None, alias="systemkey"),
    session_id: str | None = Header(default=None, alias="session-id"),
    user_id: str | None = Header(default=None, alias="user-id"),
):
    service = request.app.state.container.chat_completion_service
    try:
        ctx = service.resolve_request_context(
            req=req,
            systemkey=systemkey,
            session_id=session_id,
            user_id=user_id,
        )
    except InvalidSystemKeyError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": str(exc),
                    "type": "invalid_request_error",
                    "code": "invalid_system_key",
                }
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": str(exc),
                    "type": "invalid_request_error",
                    "code": "invalid_model",
                }
            },
        )

    if req.stream:
        return StreamingResponse(
            service.stream_chat_completion(req=req, ctx=ctx),
            media_type="text/event-stream",
            headers={"session-id": ctx.session_id, "user-id": ctx.user_id or ""},
        )

    try:
        payload = await service.create_chat_completion(req=req, ctx=ctx)
    except HttpClientTimeoutError as exc:
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "message": str(exc),
                    "type": "upstream_timeout_error",
                    "code": "llm_timeout",
                }
            },
        )
    except HttpClientResponseError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": str(exc),
                    "type": "upstream_error",
                    "code": "llm_upstream_error",
                }
            },
        )
    return JSONResponse(status_code=200, content=payload)
