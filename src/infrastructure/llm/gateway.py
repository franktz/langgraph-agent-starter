from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

from infrastructure.http.client import AsyncHttpClient
from infrastructure.http.errors import HttpClientResponseError
from infrastructure.llm.streaming import emit_stream_token
from infrastructure.logging.factory import LoggerFactory


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class LlmGateway:
    def __init__(
        self,
        *,
        logger_factory: LoggerFactory,
        http_client: AsyncHttpClient,
    ):
        self._logger = logger_factory.get_logger("infrastructure.llm")
        self._http_client = http_client

    async def stream_chat(
        self,
        *,
        llm_name: str,
        llm_config: dict[str, Any],
        messages: list[ChatMessage],
        systemkey: str,
        stream_to_client: bool = True,
    ) -> AsyncIterator[str]:
        provider = str(llm_config.get("provider", "mock") or "mock")
        if provider == "openai_compatible":
            async for chunk in self._stream_openai_compatible(
                llm_name=llm_name,
                llm_config=llm_config,
                messages=messages,
                systemkey=systemkey,
                stream_to_client=stream_to_client,
            ):
                yield chunk
            return

        async for chunk in self._stream_mock(
            llm_name=llm_name,
            llm_config=llm_config,
            messages=messages,
            systemkey=systemkey,
            stream_to_client=stream_to_client,
        ):
            yield chunk

    async def _stream_mock(
        self,
        *,
        llm_name: str,
        llm_config: dict[str, Any],
        messages: list[ChatMessage],
        systemkey: str,
        stream_to_client: bool,
    ) -> AsyncIterator[str]:
        user_text = next((m.content for m in reversed(messages) if m.role == "user"), "")
        model_name = str(llm_config.get("model", llm_name) or llm_name)
        content = f"[{systemkey}/{model_name}] {user_text or '(empty)'}"
        for index, token in enumerate(content.split(" ")):
            if index:
                await self._emit_token(" ", stream_to_client=stream_to_client)
                yield " "
            await self._emit_token(token, stream_to_client=stream_to_client)
            yield token
            await asyncio.sleep(0.01)

    async def _stream_openai_compatible(
        self,
        *,
        llm_name: str,
        llm_config: dict[str, Any],
        messages: list[ChatMessage],
        systemkey: str,
        stream_to_client: bool,
    ) -> AsyncIterator[str]:
        base_url = str(llm_config.get("base_url", "") or "").rstrip("/")
        endpoint = str(llm_config.get("endpoint", "/chat/completions") or "/chat/completions")
        model_name = str(llm_config.get("model", llm_name) or llm_name)
        timeout_ms = int(llm_config.get("timeout", 30000) or 30000)
        if not base_url:
            raise ValueError(f"llm '{llm_name}' missing base_url")

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "stream": True,
        }
        max_tokens = llm_config.get("max_tokens")
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        body = llm_config.get("body")
        if isinstance(body, Mapping):
            payload.update({str(key): value for key, value in body.items()})
        retry_config = llm_config.get("retry")

        headers = self._build_headers(llm_config=llm_config, systemkey=systemkey)
        try:
            async with self._http_client.stream(
                "POST",
                f"{base_url}{endpoint}",
                json=payload,
                headers=headers,
                timeout=timeout_ms / 1000.0,
                retry=retry_config,
            ) as response:
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        if data == "[DONE]":
                            break
                        continue
                    try:
                        chunk_payload = json.loads(data)
                    except json.JSONDecodeError:
                        self._logger.warning(
                            "openai-compatible llm stream returned non-json chunk",
                            extra={"llm_name": llm_name, "model": model_name},
                        )
                        continue
                    token = self._extract_stream_content(chunk_payload)
                    if not token:
                        continue
                    await self._emit_token(token, stream_to_client=stream_to_client)
                    yield token
        except HttpClientResponseError:
            self._logger.exception("openai-compatible llm request failed")
            raise

        self._logger.info(
            "openai-compatible llm request completed",
            extra={"llm_name": llm_name, "model": model_name},
        )

    def _build_headers(self, *, llm_config: dict[str, Any], systemkey: str) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "X-System-Key": systemkey}
        configured_headers = llm_config.get("headers")
        if isinstance(configured_headers, Mapping):
            headers.update(
                {
                    str(key): str(value)
                    for key, value in configured_headers.items()
                    if value is not None
                }
            )
        api_key = llm_config.get("apikey")
        if api_key is None:
            api_key = llm_config.get("api_key")
        if api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def _emit_token(self, token: str, *, stream_to_client: bool) -> None:
        if not stream_to_client:
            return
        await emit_stream_token(token)

    def _extract_stream_content(self, response: object) -> str:
        if not isinstance(response, dict):
            return ""
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        delta = first.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                return "".join(parts)
        text = first.get("text")
        if isinstance(text, str):
            return text
        return ""
