from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from dynamic_config.provider import DynamicConfigProvider
from workflows.demo_summary.nodes.summarize import summarize
from workflows.demo_summary.state import DemoSummaryState


def build(*, checkpointer=None, llm_client=None, workflow_config: DynamicConfigProvider | None = None):
    async def summarize_node(state, config):
        return await summarize(
            state,
            config=config,
            llm_client=llm_client,
            workflow_config=workflow_config,
        )

    builder: StateGraph = StateGraph(DemoSummaryState)
    builder.add_node("summarize", summarize_node)
    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", END)
    return builder.compile(checkpointer=checkpointer)
