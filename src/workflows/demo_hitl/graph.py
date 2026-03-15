from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from dynamic_config.provider import DynamicConfigProvider
from workflows.demo_hitl.nodes.generate import generate_draft
from workflows.demo_hitl.nodes.review import human_review
from workflows.demo_hitl.state import DemoHitlState


def build(*, checkpointer=None, workflow_config: DynamicConfigProvider | None = None):
    async def generate_node(state, config):
        return await generate_draft(
            state,
            config=config,
            workflow_config=workflow_config,
        )

    builder: StateGraph = StateGraph(DemoHitlState)
    builder.add_node("generate_draft", generate_node)
    builder.add_node("human_review", human_review)
    builder.add_edge(START, "generate_draft")
    builder.add_edge("generate_draft", "human_review")
    builder.add_edge("human_review", END)
    return builder.compile(checkpointer=checkpointer)
