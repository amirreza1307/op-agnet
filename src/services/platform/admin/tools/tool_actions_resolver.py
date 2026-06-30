"""Resolve declarative `actions` payloads for tool create/update."""
from __future__ import annotations

from typing import Any, Optional

from api.errors import BadRequestError
from setup.translator import trans
from tools.registry import get_registration, has_slug


async def resolve_tool_actions_payload(payload: dict[str, Any]) -> Optional[list[dict[str, Any]]]:
    if "actions" in payload:
        return payload.get("actions") or []

    tool_type = payload.get("tool_type")
    script_slug = payload.get("script_slug")

    if tool_type == "script":
        if not script_slug:
            raise BadRequestError(trans("errors.platform.admin.script_tool_requires_slug"))
        if not has_slug(script_slug):
            raise BadRequestError(trans("errors.platform.admin.unknown_tool_slug", slug=script_slug))

        return [
            {
                "name": payload.get("name") or get_registration(script_slug).name_fa,
                "description": payload.get("description", ""),
                "slug": script_slug,
                "constructor_params": {},
                "is_active": True,
            }
        ]

    if tool_type is not None:
        return []

    return None
