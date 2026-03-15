from __future__ import annotations

from langgraph.graph import MessagesState


class DemoChatState(MessagesState, total=False):
    systemkey: str
    user_id: str | None
    answer: str
