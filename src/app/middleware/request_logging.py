from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response

from infrastructure.logging.factory import request_id_var, session_id_var, trace_id_var


def register_request_logging_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def _request_logging(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        incoming_session_id = request.headers.get("session-id") or "-"
        token_request = request_id_var.set(request_id)
        token_session = session_id_var.set(incoming_session_id)
        token_trace = trace_id_var.set(incoming_session_id if incoming_session_id != "-" else request_id)
        request.state.request_id = request_id
        request.state.session_id = incoming_session_id if incoming_session_id != "-" else None
        logger = request.app.state.container.logger_factory.get_logger("app.http")
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.exception(
                "[HTTP] request_id=%s session=%s %s %s -> unhandled_exception elapsed_ms=%s",
                request_id,
                session_id_var.get("-"),
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise
        try:
            response.headers.setdefault("x-request-id", request_id)
            current_session_id = session_id_var.get("-")
            if current_session_id != "-" and "session-id" not in response.headers:
                response.headers["session-id"] = current_session_id

            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            if response.status_code >= 500:
                logger.error(
                    "[HTTP] request_id=%s session=%s %s %s -> status=%s elapsed_ms=%s",
                    request_id,
                    current_session_id,
                    request.method,
                    request.url.path,
                    response.status_code,
                    elapsed_ms,
                )
            return response
        finally:
            request_id_var.reset(token_request)
            session_id_var.reset(token_session)
            trace_id_var.reset(token_trace)
