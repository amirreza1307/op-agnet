"""Builder for ``knowledge`` tool variants.

Knowledge tools are DB-defined tools with no external URL and no script action.
When invoked, they return the active ``platform.tool_knowledge_nodes`` rows for
the tool's slug.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from database.repositories.main.tool_knowledge_node_repo import ToolKnowledgeNodeRepo
from services.platform.runtime.tools.agno_function_builder import (
    ToolParam,
    ToolSpec,
    build_agno_function,
)
from services.platform.runtime.tools.dynamic_tool_helpers import (
    _tool_show_result,
    _tool_stop_after_tool_call,
    _tool_stop_hooks,
)
from services.platform.runtime.tools.tool_name_sanitizer import build_tool_description

logger = logging.getLogger(__name__)


def build_knowledge_tool(
    tool_record,
    *,
    provider_name: str,
    force_direct_response: bool = False,
):
    """Build a ``knowledge`` tool as an Agno ``Function``."""
    params = tool_record.parameters or []
    tool_params = [
        ToolParam(
            name=str(p.get("name", "")),
            type=str(p.get("type", "str")),
            default=p.get("default"),
            required=bool(p.get("required", False)),
            description=p.get("description"),
            schema=p.get("schema") if isinstance(p.get("schema"), dict) else None,
        )
        for p in params
        if isinstance(p, dict) and p.get("name")
    ]
    description = build_tool_description(
        tool_record.description,
        display_name=tool_record.name,
        provider_name=provider_name,
    )

    entrypoint = _KnowledgeEntrypoint(tool_slug=str(tool_record.slug or "").strip())
    stop_after = _tool_stop_after_tool_call(tool_record, force_direct_response=force_direct_response)
    spec = ToolSpec(
        name=provider_name,
        description=description,
        parameters=tool_params,
        entrypoint=entrypoint,
        show_result=_tool_show_result(tool_record, force_direct_response=force_direct_response),
        stop_after_tool_call=stop_after,
        **_tool_stop_hooks(stop_after),
    )
    return build_agno_function(spec)


class _KnowledgeEntrypoint:
    def __init__(self, *, tool_slug: str) -> None:
        self.tool_slug = tool_slug

    async def __call__(
        self,
        kwargs: dict[str, Any],
        *,
        agent: Any = None,
        team: Any = None,
        run_context: Any = None,
    ) -> str:
        if not self.tool_slug:
            return json.dumps(
                {"knowledge_nodes": [], "tool_output": ""},
                ensure_ascii=False,
            )

        try:
            nodes = await ToolKnowledgeNodeRepo.get_active_by_tool_slug(self.tool_slug)
        except Exception:
            logger.exception("Could not load knowledge nodes for tool slug '%s'", self.tool_slug)
            raise

        payload = {
            "knowledge_nodes": [
                {
                    "title": node.title,
                    "content": node.content,
                    "priority": node.priority,
                }
                for node in nodes
            ],
            "tool_output": "",
        }
        return json.dumps(payload, ensure_ascii=False, default=str)


__all__ = ["build_knowledge_tool"]
