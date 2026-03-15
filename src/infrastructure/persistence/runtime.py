from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from langgraph.types import Command

from domain.auth.models import RequestContext
from infrastructure.config.provider import ConfigProvider
from infrastructure.llm.mock_client import MockChatClient
from infrastructure.logging.factory import LoggerFactory
from infrastructure.monitoring.langfuse import LangfuseFactory
from infrastructure.persistence.events import RuntimeEvent
from presentation.schemas.openai import ChatCompletionRequest
from workflows.registry import WorkflowRegistry


class WorkflowRuntime:
    def __init__(
        self,
        *,
        config_provider: ConfigProvider,
        logger_factory: LoggerFactory,
        workflow_registry: WorkflowRegistry,
        checkpointer_builder,
        langfuse_factory: LangfuseFactory,
        llm_client: MockChatClient,
    ) -> None:
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("infrastructure.runtime")
        self._workflow_registry = workflow_registry
        self._checkpointer_builder = checkpointer_builder
        self._langfuse_factory = langfuse_factory
        self._llm_client = llm_client
        self._checkpointer_handle = None
        self._graph_cache: dict[str, Any] = {}
        self._session_state: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        self._checkpointer_handle = await self._checkpointer_builder(self._config_provider)
        self._logger.info("workflow runtime started")

    async def stop(self) -> None:
        if self._checkpointer_handle is not None:
            await self._checkpointer_handle.close()
            self._checkpointer_handle = None
        self._logger.info("workflow runtime stopped")

    async def run_once(self, *, request: ChatCompletionRequest, ctx: RequestContext) -> dict[str, Any]:
        graph = self._get_graph(ctx.workflow)
        last_user = self._last_user_text(request) or ""
        self._logger.info("workflow invocation started", extra={"workflow": ctx.workflow})
        resume_payload = self._resume_payload(request)
        if resume_payload is not None:
            result = await graph.ainvoke(Command(resume=resume_payload), config=self._config(ctx))
        else:
            result = await graph.ainvoke(
                {"question": last_user, "systemkey": ctx.systemkey, "llm_profile": ctx.llm_profile},
                config=self._config(ctx),
            )
        if isinstance(result, dict) and result.get("__interrupt__") is not None:
            interrupt_payload = self._normalize_interrupt(result.get("__interrupt__"))
            self._session_state[ctx.session_id] = {"workflow": ctx.workflow, "interrupt": interrupt_payload}
            self._logger.info("workflow interrupted", extra={"workflow": ctx.workflow})
            return {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{uuid.uuid4().hex}",
                            "type": "function",
                            "function": {
                                "name": "human_review",
                                "arguments": json.dumps({"interrupt": interrupt_payload}, ensure_ascii=False),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        self._session_state.pop(ctx.session_id, None)
        self._logger.info("workflow completed", extra={"workflow": ctx.workflow})
        content = self._result_text(result)
        return {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}

    async def stream(
        self, *, request: ChatCompletionRequest, ctx: RequestContext, completion_id: str, created: int
    ) -> AsyncIterator[str]:
        result = await self.run_once(request=request, ctx=ctx)
        message = result["message"]
        if message.get("tool_calls"):
            event = RuntimeEvent(type="tool_calls", payload={"tool_calls": message["tool_calls"]})
            yield f"data: {json.dumps(event.to_chunk(completion_id=completion_id, created=created, workflow=ctx.workflow, session_id=ctx.session_id, user_id=ctx.user_id), ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': ctx.workflow, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'tool_calls'}], 'session_id': ctx.session_id, 'user_id': ctx.user_id}, ensure_ascii=False)}\n\n"
            return
        content = str(message.get("content") or "")
        event = RuntimeEvent(type="content", payload={"content": content})
        yield f"data: {json.dumps(event.to_chunk(completion_id=completion_id, created=created, workflow=ctx.workflow, session_id=ctx.session_id, user_id=ctx.user_id), ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': ctx.workflow, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'session_id': ctx.session_id, 'user_id': ctx.user_id}, ensure_ascii=False)}\n\n"

    def _get_graph(self, workflow: str):
        graph = self._graph_cache.get(workflow)
        if graph is not None:
            return graph
        graph = self._workflow_registry.build(
            workflow,
            checkpointer=self._checkpointer_handle.saver if self._checkpointer_handle else None,
            llm_client=self._llm_client,
        )
        self._graph_cache[workflow] = graph
        return graph

    def _config(self, ctx: RequestContext) -> dict[str, Any]:
        trace_tags = [
            f"workflow:{ctx.workflow}",
            f"systemkey:{ctx.systemkey}",
            f"llm_profile:{ctx.llm_profile}",
        ]
        config: dict[str, Any] = {
            "configurable": {"thread_id": ctx.session_id},
            "metadata": {
                "systemkey": ctx.systemkey,
                "session_id": ctx.session_id,
                "user_id": ctx.user_id,
                "workflow": ctx.workflow,
                "llm_profile": ctx.llm_profile,
                "langfuse_session_id": ctx.session_id,
                "langfuse_user_id": ctx.user_id,
                "langfuse_tags": trace_tags,
            },
            "tags": trace_tags,
        }
        langfuse_handler = self._langfuse_factory.make_handler()
        if langfuse_handler is not None:
            config["callbacks"] = [langfuse_handler]
        return config

    def _result_text(self, result: Any) -> str | None:
        if isinstance(result, dict):
            for key in ("final", "draft", "summary", "answer"):
                value = result.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    def _normalize_interrupt(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(key): self._normalize_interrupt(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._normalize_interrupt(item) for item in value]
        if hasattr(value, "value"):
            payload = getattr(value, "value")
            interrupt_id = getattr(value, "id", None)
            normalized = {"value": self._normalize_interrupt(payload)}
            if interrupt_id is not None:
                normalized["id"] = str(interrupt_id)
            return normalized
        return str(value)

    def _resume_payload(self, request: ChatCompletionRequest) -> dict[str, Any] | None:
        for message in reversed(request.messages):
            if message.role != "tool":
                continue
            content = message.content
            if isinstance(content, str):
                return {"final": content}
        return None

    def _last_user_text(self, request: ChatCompletionRequest) -> str | None:
        for message in reversed(request.messages):
            if message.role != "user":
                continue
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text")
                        if isinstance(text, str):
                            parts.append(text)
                return "".join(parts) if parts else None
        return None
