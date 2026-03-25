from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import contextmanager

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from domain.auth.errors import InvalidSysCodeError
from domain.workflows.errors import MissingWorkflowModelError
from infrastructure.http.errors import HttpClientResponseError, HttpClientTimeoutError
from infrastructure.logging.factory import request_id_var, session_id_var, trace_id_var
from presentation.schemas.openai import ChatCompletionRequest

router = APIRouter()
logger = logging.getLogger("app.api.openai")


def _response_ids(request: Request, session_id: str | None = None) -> tuple[str, str | None]:
    request_id = getattr(request.state, "request_id", "-")
    resolved_session_id = session_id or getattr(request.state, "session_id", None)
    return request_id, resolved_session_id


def _error_response(
    *,
    request: Request,
    status_code: int,
    error_message: str,
    error_type: str,
    error_code: str,
    session_id: str | None = None,
) -> JSONResponse:
    request_id, resolved_session_id = _response_ids(request, session_id)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": error_message,
                "type": error_type,
                "code": error_code,
            },
            "request_id": request_id,
            "session_id": resolved_session_id,
        },
    )


def _extract_raw_input_messages(body: object) -> list[dict[str, object]]:
    if not isinstance(body, dict):
        return []
    messages = body.get("messages")
    if not isinstance(messages, list):
        return []
    return [item for item in messages if isinstance(item, dict)]


async def _bind_stream_logging_context(
    *,
    generator: AsyncIterator[str],
    request_id: str,
    session_id: str,
    first_chunk: str | None = None,
):
    with _stream_logging_context(request_id=request_id, session_id=session_id):
        if first_chunk is not None:
            yield first_chunk
        async for chunk in generator:
            yield chunk


@contextmanager
def _stream_logging_context(*, request_id: str, session_id: str):
    token_request = request_id_var.set(request_id)
    token_session = session_id_var.set(session_id)
    token_trace = trace_id_var.set(session_id or request_id)
    try:
        yield
    finally:
        request_id_var.reset(token_request)
        session_id_var.reset(token_session)
        trace_id_var.reset(token_trace)


@router.get("/v1/models")
async def list_models(request: Request) -> dict[str, object]:
    service = request.app.state.container.workflow_catalog
    return {"object": "list", "data": service.list_models()}


@router.post("/v1/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    sys_code: str | None = Header(default=None, alias="sysCode"),
    session_id: str | None = Header(default=None, alias="session-id"),
    user_id: str | None = Header(default=None, alias="user-id"),
):
    raw_body = await request.json()
    raw_input_messages = _extract_raw_input_messages(raw_body)
    logger.info(
        "[HTTP] HTTP request received request_id=%s session=%s -> POST /v1/chat/completions model=%s stream=%s sysCode=%s messages=%s",
        getattr(request.state, "request_id", "-"),
        session_id or "-",
        req.model or "-",
        bool(req.stream),
        sys_code or "-",
        len(req.messages),
    )
    service = request.app.state.container.chat_completion_service
    try:
        ctx = service.resolve_request_context(
            req=req,
            sys_code=sys_code,
            session_id=session_id,
            user_id=user_id,
        )
        request.state.session_id = ctx.session_id
        session_id_var.set(ctx.session_id)
        trace_id_var.set(ctx.session_id)
    except InvalidSysCodeError as exc:
        return _error_response(
            request=request,
            status_code=401,
            error_message=str(exc),
            error_type="authentication_error",
            error_code="invalid_sys_code",
            session_id=session_id,
        )
    except MissingWorkflowModelError as exc:
        return _error_response(
            request=request,
            status_code=400,
            error_message=str(exc),
            error_type="invalid_request_error",
            error_code="missing_model",
            session_id=session_id,
        )
    except ValueError as exc:
        return _error_response(
            request=request,
            status_code=400,
            error_message=str(exc),
            error_type="invalid_request_error",
            error_code="invalid_model",
            session_id=session_id,
        )

    if req.stream:
        request_id, resolved_session_id = _response_ids(request, ctx.session_id)
        generator = service.stream_chat_completion(
            req=req,
            ctx=ctx,
            raw_input_messages=raw_input_messages,
        )
        try:
            with _stream_logging_context(
                request_id=request_id,
                session_id=resolved_session_id or ctx.session_id,
            ):
                first_chunk = await anext(generator)
        except HttpClientTimeoutError as exc:
            return _error_response(
                request=request,
                status_code=504,
                error_message=str(exc),
                error_type="upstream_timeout_error",
                error_code="llm_timeout",
                session_id=ctx.session_id,
            )
        except HttpClientResponseError as exc:
            return _error_response(
                request=request,
                status_code=502,
                error_message=str(exc),
                error_type="upstream_error",
                error_code="llm_upstream_error",
                session_id=ctx.session_id,
            )
        return StreamingResponse(
            _bind_stream_logging_context(
                generator=generator,
                request_id=request_id,
                session_id=resolved_session_id or ctx.session_id,
                first_chunk=first_chunk,
            ),
            media_type="text/event-stream",
            headers={
                "x-request-id": request_id,
                "session-id": ctx.session_id,
                "user-id": ctx.user_id or "",
            },
        )

    try:
        payload = await service.create_chat_completion(
            req=req,
            ctx=ctx,
            raw_input_messages=raw_input_messages,
        )
    except HttpClientTimeoutError as exc:
        return _error_response(
            request=request,
            status_code=504,
            error_message=str(exc),
            error_type="upstream_timeout_error",
            error_code="llm_timeout",
            session_id=ctx.session_id,
        )
    except HttpClientResponseError as exc:
        return _error_response(
            request=request,
            status_code=502,
            error_message=str(exc),
            error_type="upstream_error",
            error_code="llm_upstream_error",
            session_id=ctx.session_id,
        )
    return JSONResponse(status_code=200, content=payload)
