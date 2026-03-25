from __future__ import annotations

from dataclasses import dataclass

import pytest
from langgraph.types import Command

from domain.auth.models import RequestContext
from infrastructure.config.provider import ConfigProvider
from infrastructure.logging.factory import setup_logging
from infrastructure.persistence.runtime import WorkflowRuntime
from presentation.schemas.openai import ChatCompletionRequest


class DummyLangfuseFactory:
    def make_handler(self):
        return None


class DummyLlmGateway:
    pass


async def _dummy_checkpointer_builder(_config_provider):
    class _Handle:
        saver = None

        async def close(self):
            return None

    return _Handle()


@dataclass(frozen=True)
class _Spec:
    supports_conversation: bool = False


class _Graph:
    def __init__(self, result):
        self.result = result
        self.calls: list[tuple[object, dict]] = []

    async def ainvoke(self, payload, config=None):  # type: ignore[no-untyped-def]
        self.calls.append((payload, config or {}))
        return self.result


class _Registry:
    def __init__(self, graph: _Graph):
        self.graph = graph

    def get_spec(self, _workflow: str) -> _Spec:
        return _Spec()

    def build(self, _workflow: str, *, checkpointer=None):  # type: ignore[no-untyped-def]
        return self.graph


def _runtime_with_graph(graph: _Graph) -> WorkflowRuntime:
    provider = ConfigProvider(local_yaml_path="configs/local.yaml")
    provider.load_from_env()
    logger_factory = setup_logging(provider)
    return WorkflowRuntime(
        config_provider=provider,
        logger_factory=logger_factory,
        workflow_registry=_Registry(graph),  # type: ignore[arg-type]
        checkpointer_builder=_dummy_checkpointer_builder,
        langfuse_factory=DummyLangfuseFactory(),
        llm_gateway=DummyLlmGateway(),  # type: ignore[arg-type]
    )


def _ctx() -> RequestContext:
    return RequestContext(
        sys_code="demo-system",
        session_id="session-123",
        user_id="user-1",
        workflow="demo-summary",
    )


@pytest.mark.asyncio
async def test_run_once_non_conversation_passes_input_and_raw_messages() -> None:
    graph = _Graph(result={"summary": "ok"})
    runtime = _runtime_with_graph(graph)
    request = ChatCompletionRequest(
        model="demo-summary",
        messages=[
            {"role": "user", "content": "Summarize this"},
        ],
    )
    raw_input_messages = [
        {
            "role": "user",
            "content": "Summarize this",
            "extra_field": "keep-raw",
        }
    ]

    result = await runtime.run_once(
        request=request,
        ctx=_ctx(),
        raw_input_messages=raw_input_messages,
    )

    assert result["message"]["content"] == "ok"
    payload, _config = graph.calls[0]
    assert payload == {
        "input_messages": [
            {
                "role": "user",
                "content": "Summarize this",
                "name": None,
                "tool_call_id": None,
            }
        ],
        "raw_input_messages": raw_input_messages,
        "sys_code": "demo-system",
    }


@pytest.mark.asyncio
async def test_run_once_resume_overwrites_input_and_raw_messages() -> None:
    graph = _Graph(result={"final": "done"})
    runtime = _runtime_with_graph(graph)
    request = ChatCompletionRequest(
        model="demo-hitl",
        messages=[
            {"role": "user", "content": "Write release note"},
            {"role": "assistant", "content": None},
            {"role": "tool", "tool_call_id": "call-1", "content": "Emphasize canary release"},
        ],
    )
    raw_input_messages = [
        {"role": "user", "content": "Write release note"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call-1"}]},
        {"role": "tool", "tool_call_id": "call-1", "content": "Emphasize canary release"},
    ]

    result = await runtime.run_once(
        request=request,
        ctx=_ctx(),
        raw_input_messages=raw_input_messages,
    )

    assert result["message"]["content"] == "done"
    payload, _config = graph.calls[0]
    assert isinstance(payload, Command)
    assert payload.resume == {"final": "Emphasize canary release"}
    assert payload.update == {
        "input_messages": [
            {"role": "user", "content": "Write release note", "name": None, "tool_call_id": None},
            {"role": "assistant", "content": None, "name": None, "tool_call_id": None},
            {"role": "tool", "content": "Emphasize canary release", "name": None, "tool_call_id": "call-1"},
        ],
        "raw_input_messages": raw_input_messages,
        "sys_code": "demo-system",
    }
