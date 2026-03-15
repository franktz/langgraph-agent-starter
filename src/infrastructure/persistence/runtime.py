from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Command

from domain.auth.models import RequestContext
from infrastructure.config.provider import ConfigProvider
from infrastructure.llm.context import bind_llm_gateway
from infrastructure.llm.streaming import bind_stream_writer
from infrastructure.llm.gateway import LlmGateway
from infrastructure.logging.factory import LoggerFactory, request_id_var
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
        llm_gateway: LlmGateway,
    ) -> None:
        self._config_provider = config_provider
        self._logger = logger_factory.get_logger("infrastructure.runtime")
        self._workflow_registry = workflow_registry
        self._checkpointer_builder = checkpointer_builder
        self._langfuse_factory = langfuse_factory
        self._llm_gateway = llm_gateway
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
        spec = self._workflow_registry.get_spec(ctx.workflow)
        last_user = self._last_user_text(request) or ""
        self._logger.info(
            "[FLOW] workflow=%s session=%s user=%s -> run:start",
            ctx.workflow,
            ctx.session_id,
            ctx.user_id or "-",
            extra={
                "workflow": ctx.workflow,
                "session_id": ctx.session_id,
                "user_id": ctx.user_id,
            },
        )
        if spec.supports_conversation:
            existing_messages = await self._current_messages(graph=graph, ctx=ctx)
            incoming_messages = self._normalize_request_messages(request)
            delta_messages = self._messages_delta(existing=existing_messages, incoming=incoming_messages)
            if not delta_messages:
                cached_answer = self._last_assistant_text(existing_messages)
                if cached_answer is not None:
                    self._logger.info(
                        "[CHAT] workflow=%s session=%s -> history:reused persisted=%s incoming=%s",
                        ctx.workflow,
                        ctx.session_id,
                        len(existing_messages),
                        len(incoming_messages),
                        extra={
                            "workflow": ctx.workflow,
                            "session_id": ctx.session_id,
                            "persisted_messages": len(existing_messages),
                            "incoming_messages": len(incoming_messages),
                        },
                    )
                    return {
                        "index": 0,
                        "message": {"role": "assistant", "content": cached_answer},
                        "finish_reason": "stop",
                    }
            self._logger.info(
                "[CHAT] workflow=%s session=%s -> history:merge persisted=%s incoming=%s append=%s thread=%s",
                ctx.workflow,
                ctx.session_id,
                len(existing_messages),
                len(incoming_messages),
                len(delta_messages),
                ctx.thread_id,
                extra={
                    "workflow": ctx.workflow,
                    "session_id": ctx.session_id,
                    "persisted_messages": len(existing_messages),
                    "incoming_messages": len(incoming_messages),
                    "appended_messages": len(delta_messages),
                    "thread_id": ctx.thread_id,
                },
            )
            with bind_llm_gateway(self._llm_gateway):
                result = await graph.ainvoke(
                    {
                        "messages": delta_messages,
                        "systemkey": ctx.systemkey,
                        "user_id": ctx.user_id,
                    },
                    config=self._config(ctx),
                )
            content = self._result_text(result)
            self._logger.info(
                "[FLOW] workflow=%s session=%s -> run:completed output=%r",
                ctx.workflow,
                ctx.session_id,
                self._preview_text(content),
                extra={
                    "workflow": ctx.workflow,
                    "session_id": ctx.session_id,
                    "output_preview": self._preview_text(content),
                },
            )
            return {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        resume_payload = self._resume_payload(request)
        if resume_payload is not None:
            self._logger.info(
                "[FLOW] workflow=%s session=%s -> resume:received payload=%s",
                ctx.workflow,
                ctx.session_id,
                resume_payload,
                extra={"workflow": ctx.workflow, "session_id": ctx.session_id, "resume_payload": resume_payload},
            )
            with bind_llm_gateway(self._llm_gateway):
                result = await graph.ainvoke(Command(resume=resume_payload), config=self._config(ctx))
        else:
            self._logger.info(
                "[FLOW] workflow=%s session=%s -> input:accepted question=%r",
                ctx.workflow,
                ctx.session_id,
                self._preview_text(last_user),
                extra={
                    "workflow": ctx.workflow,
                    "session_id": ctx.session_id,
                    "question_preview": self._preview_text(last_user),
                },
            )
            with bind_llm_gateway(self._llm_gateway):
                result = await graph.ainvoke(
                    {"question": last_user, "systemkey": ctx.systemkey},
                    config=self._config(ctx),
                )
        if isinstance(result, dict) and result.get("__interrupt__") is not None:
            interrupt_payload = self._normalize_interrupt(result.get("__interrupt__"))
            self._session_state[ctx.thread_id] = {"workflow": ctx.workflow, "interrupt": interrupt_payload}
            self._logger.info(
                "[HITL] workflow=%s session=%s -> interrupt:waiting_human_input payload=%s",
                ctx.workflow,
                ctx.session_id,
                interrupt_payload,
                extra={
                    "workflow": ctx.workflow,
                    "session_id": ctx.session_id,
                    "interrupt_payload": interrupt_payload,
                },
            )
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
        self._session_state.pop(ctx.thread_id, None)
        self._logger.info(
            "[FLOW] workflow=%s session=%s -> run:completed output=%r",
            ctx.workflow,
            ctx.session_id,
            self._preview_text(self._result_text(result)),
            extra={
                "workflow": ctx.workflow,
                "session_id": ctx.session_id,
                "output_preview": self._preview_text(self._result_text(result)),
            },
        )
        content = self._result_text(result)
        return {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}

    async def stream(
        self, *, request: ChatCompletionRequest, ctx: RequestContext, completion_id: str, created: int
    ) -> AsyncIterator[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        streamed_chunk_count = 0
        streamed_char_count = 0

        async def _write_token(token: str) -> None:
            await queue.put(token)

        async def _run_with_stream_writer() -> dict[str, Any]:
            with bind_stream_writer(_write_token):
                return await self.run_once(request=request, ctx=ctx)

        task = asyncio.create_task(_run_with_stream_writer())
        self._logger.info(
            "[STREAM] workflow=%s session=%s -> stream:open",
            ctx.workflow,
            ctx.session_id,
            extra={"workflow": ctx.workflow, "session_id": ctx.session_id},
        )
        try:
            while True:
                if task.done() and queue.empty():
                    break
                try:
                    token = await asyncio.wait_for(queue.get(), timeout=0.05)
                except asyncio.TimeoutError:
                    continue
                streamed_chunk_count += 1
                streamed_char_count += len(token)
                if streamed_chunk_count == 1:
                    self._logger.info(
                        "[STREAM] workflow=%s session=%s -> stream:first_delta chunk=%r",
                        ctx.workflow,
                        ctx.session_id,
                        self._preview_text(token, limit=40),
                        extra={
                            "workflow": ctx.workflow,
                            "session_id": ctx.session_id,
                            "stream_chunk_preview": self._preview_text(token, limit=40),
                        },
                    )
                event = RuntimeEvent(type="content", payload={"content": token})
                yield f"data: {json.dumps(event.to_chunk(completion_id=completion_id, created=created, workflow=ctx.workflow, session_id=ctx.session_id, user_id=ctx.user_id), ensure_ascii=False)}\n\n"
            result = await task
        except Exception:
            if not task.done():
                task.cancel()
            raise

        message = result["message"]
        if message.get("tool_calls"):
            self._logger.info(
                "[STREAM] workflow=%s session=%s -> stream:interrupt tool_calls chunks=%s chars=%s",
                ctx.workflow,
                ctx.session_id,
                streamed_chunk_count,
                streamed_char_count,
                extra={
                    "workflow": ctx.workflow,
                    "session_id": ctx.session_id,
                    "stream_chunk_count": streamed_chunk_count,
                    "stream_char_count": streamed_char_count,
                },
            )
            event = RuntimeEvent(type="tool_calls", payload={"tool_calls": message["tool_calls"]})
            yield f"data: {json.dumps(event.to_chunk(completion_id=completion_id, created=created, workflow=ctx.workflow, session_id=ctx.session_id, user_id=ctx.user_id), ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': ctx.workflow, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'tool_calls'}], 'session_id': ctx.session_id, 'user_id': ctx.user_id}, ensure_ascii=False)}\n\n"
            return
        content = str(message.get("content") or "")
        if streamed_chunk_count == 0 and content:
            self._logger.info(
                "[STREAM] workflow=%s session=%s -> stream:fallback_single_chunk content=%r",
                ctx.workflow,
                ctx.session_id,
                self._preview_text(content),
                extra={
                    "workflow": ctx.workflow,
                    "session_id": ctx.session_id,
                    "content_preview": self._preview_text(content),
                },
            )
            event = RuntimeEvent(type="content", payload={"content": content})
            yield f"data: {json.dumps(event.to_chunk(completion_id=completion_id, created=created, workflow=ctx.workflow, session_id=ctx.session_id, user_id=ctx.user_id), ensure_ascii=False)}\n\n"
            streamed_chunk_count = 1
            streamed_char_count = len(content)
        self._logger.info(
            "[STREAM] workflow=%s session=%s -> stream:finish finish_reason=stop chunks=%s chars=%s",
            ctx.workflow,
            ctx.session_id,
            streamed_chunk_count,
            streamed_char_count,
            extra={
                "workflow": ctx.workflow,
                "session_id": ctx.session_id,
                "stream_chunk_count": streamed_chunk_count,
                "stream_char_count": streamed_char_count,
            },
        )
        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': ctx.workflow, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'session_id': ctx.session_id, 'user_id': ctx.user_id}, ensure_ascii=False)}\n\n"

    def _get_graph(self, workflow: str):
        graph = self._graph_cache.get(workflow)
        if graph is not None:
            return graph
        graph = self._workflow_registry.build(
            workflow,
            checkpointer=self._checkpointer_handle.saver if self._checkpointer_handle else None,
        )
        self._graph_cache[workflow] = graph
        return graph

    def _config(self, ctx: RequestContext, *, include_callbacks: bool = True) -> dict[str, Any]:
        request_id = request_id_var.get("-")
        trace_tags = [
            f"workflow:{ctx.workflow}",
            f"systemkey:{ctx.systemkey}",
            f"request_id:{request_id}",
        ]
        config: dict[str, Any] = {
            "configurable": {"thread_id": ctx.thread_id},
            "metadata": {
                "request_id": request_id,
                "systemkey": ctx.systemkey,
                "session_id": ctx.session_id,
                "user_id": ctx.user_id,
                "workflow": ctx.workflow,
                "langfuse_request_id": request_id,
                "langfuse_session_id": ctx.session_id,
                "langfuse_user_id": ctx.user_id,
                "langfuse_tags": trace_tags,
            },
            "tags": trace_tags,
        }
        langfuse_handler = self._langfuse_factory.make_handler() if include_callbacks else None
        if langfuse_handler is not None:
            config["callbacks"] = [langfuse_handler]
        return config

    async def _current_messages(self, *, graph, ctx: RequestContext) -> list[BaseMessage]:
        snapshot = await graph.aget_state(self._config(ctx, include_callbacks=False))
        values = snapshot.values if hasattr(snapshot, "values") else {}
        if not isinstance(values, dict):
            return []
        raw_messages = values.get("messages", [])
        if not isinstance(raw_messages, list):
            return []
        return [message for message in raw_messages if isinstance(message, BaseMessage)]

    def _normalize_request_messages(self, request: ChatCompletionRequest) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for index, message in enumerate(request.messages):
            normalized = self._normalize_request_message(message=message, index=index)
            if normalized is not None:
                messages.append(normalized)
        return messages

    def _normalize_request_message(self, *, message, index: int) -> BaseMessage | None:
        content = self._message_text(message.content)
        role = str(message.role or "").strip().lower()
        if role == "assistant":
            if not content:
                return None
            return AIMessage(content=content)
        if role == "system":
            if not content:
                return None
            return SystemMessage(content=content)
        if role == "tool":
            if not content:
                return None
            tool_call_id = message.tool_call_id or f"tool-{index}"
            return ToolMessage(content=content, tool_call_id=tool_call_id)
        if not content:
            return None
        return HumanMessage(content=content)

    def _message_text(self, content: str | list[dict[str, Any]] | None) -> str:
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "text":
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)

    def _messages_delta(self, *, existing: list[BaseMessage], incoming: list[BaseMessage]) -> list[BaseMessage]:
        if not existing or not incoming:
            return list(incoming)
        existing_projection = [self._message_projection(message) for message in existing]
        incoming_projection = [self._message_projection(message) for message in incoming]

        common_prefix = 0
        for left, right in zip(existing_projection, incoming_projection):
            if left != right:
                break
            common_prefix += 1
        if common_prefix:
            return incoming[common_prefix:]

        overlap_limit = min(len(existing_projection), len(incoming_projection))
        for size in range(overlap_limit, 0, -1):
            if existing_projection[-size:] == incoming_projection[:size]:
                return incoming[size:]
        return list(incoming)

    def _message_projection(self, message: BaseMessage) -> tuple[str, str, str | None, str | None]:
        role = getattr(message, "type", "user")
        content = self._base_message_text(message)
        name = getattr(message, "name", None)
        tool_call_id = getattr(message, "tool_call_id", None)
        return role, content, name, tool_call_id

    def _base_message_text(self, message: BaseMessage) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return str(content or "")
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)

    def _last_assistant_text(self, messages: list[BaseMessage]) -> str | None:
        for message in reversed(messages):
            if getattr(message, "type", "") != "ai":
                continue
            content = self._base_message_text(message)
            if content:
                return content
        return None

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
            content = self._message_text(message.content)
            if content:
                return content
        return None

    @staticmethod
    def _preview_text(value: str | None, *, limit: int = 80) -> str:
        if not value:
            return ""
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[:limit]}..."
