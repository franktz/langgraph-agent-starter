from __future__ import annotations

from typing import Any


def preview_text(value: str | None, *, limit: int = 80) -> str:
    if not value:
        return ""
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def config_metadata(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    metadata = config.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}
