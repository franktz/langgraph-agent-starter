from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from infrastructure.config.provider import ConfigProvider
from infrastructure.http.client import AsyncHttpClient
from infrastructure.http.errors import HttpClientResponseError
from infrastructure.logging.factory import LoggerFactory


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class MockChatClient:
    def __init__(
        self,
        *,
        config_provider: ConfigProvider,
        logger_factory: LoggerFactory,
        http_client: AsyncHttpClient,
    ):
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("infrastructure.llm")
        self._http_client = http_client

    async def stream_chat(
        self, *, model: str, messages: list[ChatMessage], systemkey: str
    ) -> AsyncIterator[str]:
        profile = self._profile(model)
        provider = str(profile.get("provider", "mock") or "mock")
        if provider == "openai_compatible":
            async for chunk in self._stream_openai_compatible(
                profile_name=model,
                profile=profile,
                messages=messages,
                systemkey=systemkey,
            ):
                yield chunk
            return

        async for chunk in self._stream_mock(model=model, messages=messages, systemkey=systemkey):
            yield chunk

    def _profile(self, profile_name: str):
        return self._config_provider.conf["llm.profiles"][profile_name]

    async def _stream_mock(
        self, *, model: str, messages: list[ChatMessage], systemkey: str
    ) -> AsyncIterator[str]:
        user_text = next((m.content for m in reversed(messages) if m.role == "user"), "")
        content = f"[{systemkey}/{model}] {user_text or '(empty)'}"
        for index, token in enumerate(content.split(" ")):
            if index:
                yield " "
            yield token
            await asyncio.sleep(0.01)

    async def _stream_openai_compatible(
        self,
        *,
        profile_name: str,
        profile,
        messages: list[ChatMessage],
        systemkey: str,
    ) -> AsyncIterator[str]:
        base_url = str(profile.get("base_url", "") or "").rstrip("/")
        model_name = str(profile.get("model", profile_name) or profile_name)
        api_key = str(profile.get("api_key", "dummy-key") or "dummy-key")
        timeout_s = float(profile.get("timeout_s", 30) or 30)
        if not base_url:
            raise ValueError(f"llm profile '{profile_name}' missing base_url")

        payload = {
            "model": model_name,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-System-Key": systemkey,
        }
        try:
            response = await self._http_client.post_json(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout_s,
            )
        except HttpClientResponseError:
            self._logger.exception("openai-compatible llm request failed")
            raise

        content = self._extract_content(response)
        self._logger.info(
            "openai-compatible llm request completed",
            extra={"profile": profile_name, "model": model_name},
        )
        yield content

    def _extract_content(self, response: object) -> str:
        if not isinstance(response, dict):
            return str(response)
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return str(response)
        first = choices[0]
        if not isinstance(first, dict):
            return str(first)
        message = first.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
        text = first.get("text")
        if isinstance(text, str):
            return text
        return str(first)
