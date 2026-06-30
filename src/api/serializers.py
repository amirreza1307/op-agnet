from __future__ import annotations

from datetime import datetime
from typing import Any


def serialize_response_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return _sanitize_mapping(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, list):
        return [serialize_response_value(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_response_value(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()

    try:
        raw_items = vars(value).items()
    except TypeError:
        return value

    return _sanitize_mapping(dict(raw_items))


def _sanitize_mapping(data: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, item in data.items():
        if _should_skip_field(key, item):
            continue
        sanitized[key] = serialize_response_value(item)
    return sanitized


def _should_skip_field(key: str, value: Any) -> bool:
    if key.startswith("_"):
        return True
    if key.startswith("x_") and key != "x_ref":
        return True
    if callable(value):
        return True
    return False

