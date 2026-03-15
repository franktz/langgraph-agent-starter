from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from infrastructure.config.provider import ConfigProvider
from infrastructure.http.errors import HttpClientResponseError, HttpClientTimeoutError
from infrastructure.logging.factory import LoggerFactory

T = TypeVar("T")


def with_http_retry(config_provider: ConfigProvider) -> Callable:
    def _decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def _wrapper(*args, **kwargs) -> T:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(int(config_provider.get("http.retry.attempts", 3))),
                wait=wait_exponential(
                    multiplier=float(config_provider.get("http.retry.min_wait_s", 0.2)),
                    max=float(config_provider.get("http.retry.max_wait_s", 2.0)),
                ),
                retry=retry_if_exception_type(httpx.HTTPError),
                reraise=True,
            ):
                with attempt:
                    return await func(*args, **kwargs)
            raise AssertionError("unreachable")

        return _wrapper

    return _decorator


class AsyncHttpClient:
    def __init__(self, *, config_provider: ConfigProvider, logger_factory: LoggerFactory):
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("infrastructure.http")
        self._client = httpx.AsyncClient(timeout=30)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        decorated = with_http_retry(self._config_provider)(self._client.request)
        try:
            response = await decorated(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise HttpClientTimeoutError(f"request timed out: {method} {url}") from exc
        except httpx.HTTPError:
            raise
        if response.status_code >= 400:
            raise HttpClientResponseError(
                status_code=response.status_code,
                message=f"http request failed: {method} {url} -> {response.status_code}",
            )
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

    async def aclose(self) -> None:
        await self._client.aclose()
