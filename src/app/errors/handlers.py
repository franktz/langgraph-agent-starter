from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _response_ids(request: Request) -> tuple[str, str | None]:
    return getattr(request.state, "request_id", "-"), getattr(request.state, "session_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id, session_id = _response_ids(request)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": str(exc.detail),
                    "type": "http_error",
                    "code": str(exc.status_code),
                },
                "request_id": request_id,
                "session_id": session_id,
            },
            headers={"x-request-id": request_id, "session-id": session_id or ""},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id, session_id = _response_ids(request)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": "request validation failed",
                    "type": "invalid_request_error",
                    "code": "validation_error",
                    "details": exc.errors(),
                },
                "request_id": request_id,
                "session_id": session_id,
            },
            headers={"x-request-id": request_id, "session-id": session_id or ""},
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id, session_id = _response_ids(request)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "internal server error",
                    "type": "internal_server_error",
                    "code": "internal_error",
                },
                "request_id": request_id,
                "session_id": session_id,
            },
            headers={"x-request-id": request_id, "session-id": session_id or ""},
        )
