"""JSON-friendly serialization helpers shared across services (F-18)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def serialize_content(value: Any) -> Any:
    """Recursively convert ``value`` into JSON-safe primitives.

    Pydantic models become ``model_dump(mode="json")`` dicts; arbitrary
    objects fall back to ``str()`` then ``repr()``. Datetimes serialize to
    ISO 8601.
    """
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            pass
    if isinstance(value, dict):
        return {key: serialize_content(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_content(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return str(value)
    except Exception:
        return repr(value)
