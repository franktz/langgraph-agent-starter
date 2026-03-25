from __future__ import annotations

from collections.abc import Collection
from typing import Any


def last_text_from_input_messages(
    messages: Any,
    roles: str | Collection[str] | None = None,
) -> str:
    if not isinstance(messages, list):
        return ""
    allowed_roles = _normalize_roles(roles)
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip().lower()
        if role not in allowed_roles:
            continue
        content = _message_text(message.get("content"))
        if content:
            return content
    return ""


def _normalize_roles(roles: str | Collection[str] | None) -> set[str]:
    if roles is None:
        return {"tool", "user"}
    if isinstance(roles, str):
        normalized = roles.strip().lower()
        return {normalized} if normalized else {"tool", "user"}
    normalized_roles = {
        str(role).strip().lower()
        for role in roles
        if str(role).strip()
    }
    return normalized_roles or {"tool", "user"}


def _message_text(content: Any) -> str:
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
