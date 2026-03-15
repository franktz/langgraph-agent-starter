from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from infrastructure.http.errors import HttpClientResponseError, HttpClientTimeoutError
from infrastructure.logging.factory import LoggerFactory

T = TypeVar("T")


@dataclass(frozen=True)
class HttpRetryConfig:
    attempts: int
    min_wait_ms: int = 200
    max_wait_ms: int = 2000


def _is_retryable_exception(exc: BaseException) -> bool:
    if isinstance(exc, HttpClientResponseError):
        return exc.status_code in {408, 409, 429} or 500 <= exc.status_code < 600
    return isinstance(exc, (HttpClientTimeoutError, httpx.HTTPError))


def with_http_retry(retry_config: HttpRetryConfig | None) -> Callable:
    def _decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def _wrapper(*args, **kwargs) -> T:
            if retry_config is None or retry_config.attempts <= 1:
                return await func(*args, **kwargs)
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(retry_config.attempts),
                wait=wait_exponential(
                    multiplier=retry_config.min_wait_ms / 1000.0,
                    max=retry_config.max_wait_ms / 1000.0,
                ),
                retry=retry_if_exception(_is_retryable_exception),
                reraise=True,
            ):
                with attempt:
                    return await func(*args, **kwargs)
            raise AssertionError("unreachable")

        return _wrapper

    return _decorator


class AsyncHttpClient:
    def __init__(self, *, logger_factory: LoggerFactory):
        self._logger = logger_factory.get_logger("infrastructure.http")
        self._client = httpx.AsyncClient(timeout=30)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        retry_config = self._normalize_retry_config(kwargs.pop("retry", None))

        async def _send_once() -> httpx.Response:
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                raise HttpClientTimeoutError(f"request timed out: {method} {url}") from exc
            if response.status_code >= 400:
                raise HttpClientResponseError(
                    status_code=response.status_code,
                    message=f"http request failed: {method} {url} -> {response.status_code}",
                )
            return response

        decorated = with_http_retry(retry_config)(_send_once)
        response = await decorated()
        return response

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        response = await self.get(url, **kwargs)
        return response.json()

    async def post_json(self, url: str, **kwargs: Any) -> Any:
        response = await self.post(url, **kwargs)
        return response.json()

    @asynccontextmanager
    async def stream(self, method: str, url: str, **kwargs: Any):
        retry_config = self._normalize_retry_config(kwargs.pop("retry", None))
        request = self._client.build_request(method, url, **kwargs)

        async def _send_once() -> httpx.Response:
            try:
                response = await self._client.send(request, stream=True)
            except httpx.TimeoutException as exc:
                raise HttpClientTimeoutError(f"request timed out: {method} {url}") from exc
            if response.status_code >= 400:
                await response.aread()
                await response.aclose()
                raise HttpClientResponseError(
                    status_code=response.status_code,
                    message=f"http request failed: {method} {url} -> {response.status_code}",
                )
            return response

        decorated = with_http_retry(retry_config)(_send_once)
        response = await decorated()
        try:
            yield response
        finally:
            await response.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _normalize_retry_config(self, value: object) -> HttpRetryConfig | None:
        if value is None:
            return None
        if isinstance(value, HttpRetryConfig):
            return value if value.attempts > 1 else None
        if not isinstance(value, Mapping):
            return None
        attempts = int(value.get("attempts", 3) or 3)
        if attempts <= 1:
            return None
        min_wait_ms = int(value.get("min_wait", 200) or 200)
        max_wait_ms = int(value.get("max_wait", 2000) or 2000)
        return HttpRetryConfig(
            attempts=attempts,
            min_wait_ms=min_wait_ms,
            max_wait_ms=max_wait_ms,
        )
