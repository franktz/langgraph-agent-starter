import httpx
import pytest

from infrastructure.http.client import HttpRetryConfig, with_http_retry
from infrastructure.http.errors import HttpClientResponseError


@pytest.mark.anyio
async def test_with_http_retry_skips_retry_when_config_is_none() -> None:
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("boom")

    decorated = with_http_retry(None)(flaky)

    with pytest.raises(httpx.ConnectError):
        await decorated()

    assert attempts == 1


@pytest.mark.anyio
async def test_with_http_retry_retries_retryable_response_errors() -> None:
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise HttpClientResponseError(status_code=503, message="service unavailable")
        return "ok"

    decorated = with_http_retry(
        HttpRetryConfig(attempts=3, min_wait_ms=1, max_wait_ms=2),
    )(flaky)

    result = await decorated()

    assert result == "ok"
    assert attempts == 3


@pytest.mark.anyio
async def test_with_http_retry_does_not_retry_non_retryable_response_errors() -> None:
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        raise HttpClientResponseError(status_code=400, message="bad request")

    decorated = with_http_retry(
        HttpRetryConfig(attempts=3, min_wait_ms=1, max_wait_ms=2),
    )(flaky)

    with pytest.raises(HttpClientResponseError):
        await decorated()

    assert attempts == 1
