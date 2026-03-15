from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from dynamic_config.provider import DynamicConfigProvider
from workflows.demo_chat.nodes.chat import chat
from workflows.demo_chat.state import DemoChatState


def build(*, checkpointer=None, workflow_config: DynamicConfigProvider | None = None):
    async def chat_node(state, config):
        return await chat(
            state,
            config=config,
            workflow_config=workflow_config,
        )

    builder: StateGraph = StateGraph(DemoChatState)
    builder.add_node("chat", chat_node)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    return builder.compile(checkpointer=checkpointer)
