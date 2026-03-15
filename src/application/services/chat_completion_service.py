from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator

from domain.auth.errors import InvalidSystemKeyError
from domain.auth.models import RequestContext
from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import LoggerFactory
from infrastructure.persistence.runtime import WorkflowRuntime
from application.services.routing_service import RoutingService
from application.services.workflow_catalog_service import WorkflowCatalogService
from presentation.schemas.openai import ChatCompletionRequest


class ChatCompletionService:
    def __init__(
        self,
        *,
        config_provider: ConfigProvider,
        logger_factory: LoggerFactory,
        workflow_catalog: WorkflowCatalogService,
        routing_service: RoutingService,
        workflow_runtime: WorkflowRuntime,
    ) -> None:
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("application.chat_completion")
        self._workflow_catalog = workflow_catalog
        self._routing_service = routing_service
        self._workflow_runtime = workflow_runtime

    def build_usage(self, *, req: ChatCompletionRequest, output_text: str | None = None) -> dict[str, int]:
        prompt_chars = 0
        for message in req.messages:
            content = message.content
            if isinstance(content, str):
                prompt_chars += len(content)
                continue
            if not isinstance(content, list):
                continue
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str):
                        prompt_chars += len(text)
        completion_chars = len(output_text or "")
        return {
            "prompt_tokens": prompt_chars,
            "completion_tokens": completion_chars,
            "total_tokens": prompt_chars + completion_chars,
        }

    def resolve_request_context(
        self,
        *,
        req: ChatCompletionRequest,
        system_key: str | None,
        session_id: str | None,
        user_id: str | None,
    ) -> RequestContext:
        validate = bool(self._config_provider.get("api.auth.validate_system_key", False))
        effective_system_key = system_key or "default-system"
        if validate:
            systems = self._config_provider.get("api.auth.systems", [])
            keys = {item.get("key") for item in systems if isinstance(item, dict)}
            if effective_system_key not in keys:
                raise InvalidSystemKeyError(f"unknown systemKey: {effective_system_key}")
        route = self._routing_service.resolve(model=req.model, system_key=effective_system_key)
        return RequestContext(
            system_key=effective_system_key,
            session_id=session_id or uuid.uuid4().hex,
            user_id=user_id,
            workflow=route.workflow,
            llm_profile=route.llm_profile,
        )

    async def create_chat_completion(self, *, req: ChatCompletionRequest, ctx: RequestContext) -> dict[str, object]:
        created = int(time.time())
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        result = await self._workflow_runtime.run_once(request=req, ctx=ctx)
        message = result.get("message", {}) if isinstance(result, dict) else {}
        output_text = message.get("content") if isinstance(message, dict) else None
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": ctx.workflow,
            "choices": [result],
            "session_id": ctx.session_id,
            "user_id": ctx.user_id,
            "usage": self.build_usage(req=req, output_text=output_text if isinstance(output_text, str) else None),
        }

    async def stream_chat_completion(
        self, *, req: ChatCompletionRequest, ctx: RequestContext
    ) -> AsyncIterator[str]:
        created = int(time.time())
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"
        first_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": ctx.workflow,
            "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            "session_id": ctx.session_id,
            "user_id": ctx.user_id,
        }
        yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"
        async for chunk in self._workflow_runtime.stream(request=req, ctx=ctx, completion_id=completion_id, created=created):
            yield chunk
        yield "data: [DONE]\n\n"
