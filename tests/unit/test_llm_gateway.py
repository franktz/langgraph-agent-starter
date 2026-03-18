from contextlib import asynccontextmanager

import pytest

from infrastructure.config.provider import ConfigProvider
from infrastructure.http.errors import HttpClientResponseError
from infrastructure.llm.gateway import LlmGateway
from infrastructure.logging.factory import setup_logging


def _build_gateway() -> LlmGateway:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    logger_factory = setup_logging(provider)
    return LlmGateway(
        logger_factory=logger_factory,
        http_client=object(),  # type: ignore[arg-type]
    )


def test_llm_gateway_build_headers_applies_apikey_and_defaults() -> None:
    gateway = _build_gateway()

    headers = gateway._build_headers(  # type: ignore[attr-defined]
        llm_config={"apikey": "secret-token"},
        systemkey="demo-system",
    )

    assert headers["Content-Type"] == "application/json"
    assert headers["X-System-Key"] == "demo-system"
    assert headers["Authorization"] == "Bearer secret-token"


def test_llm_gateway_build_headers_merges_optional_headers() -> None:
    gateway = _build_gateway()

    headers = gateway._build_headers(  # type: ignore[attr-defined]
        llm_config={"headers": {"X-Tenant": "tenant-a"}},
        systemkey="demo-system",
    )

    assert headers["Content-Type"] == "application/json"
    assert headers["X-System-Key"] == "demo-system"
    assert headers["X-Tenant"] == "tenant-a"
    assert "Authorization" not in headers


class _FakeStreamResponse:
    def __init__(self, *, lines: list[str]) -> None:
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeHttpClient:
    def __init__(self, *, lines: list[str]) -> None:
        self._lines = lines

    @asynccontextmanager
    async def stream(self, *args, **kwargs):
        yield _FakeStreamResponse(lines=self._lines)


@pytest.mark.anyio
async def test_llm_gateway_stream_openai_compatible_raises_on_error_chunk() -> None:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    logger_factory = setup_logging(provider)
    gateway = LlmGateway(
        logger_factory=logger_factory,
        http_client=_FakeHttpClient(
            lines=[
                'data: {"error":{"message":"upstream stream failed","status":502}}',
                "data: [DONE]",
            ]
        ),  # type: ignore[arg-type]
    )

    with pytest.raises(HttpClientResponseError, match="upstream stream failed"):
        async for _ in gateway.stream_chat(
            llm_name="default",
            llm_config={
                "provider": "openai_compatible",
                "base_url": "https://example.invalid",
                "endpoint": "/chat/completions",
                "model": "demo-model",
            },
            messages=[],
            systemkey="demo-system",
        ):
            pass
