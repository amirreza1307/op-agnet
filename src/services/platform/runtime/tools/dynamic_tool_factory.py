"""Dynamic Tool Factory — creates Agno-compatible tools from DB configuration.

Tool types:
  * ``api``    — HTTP request, parameters from the Tool row.
  * ``script`` — Service-class methods bound via ToolAction rows.
"""
from __future__ import annotations

from typing import List, Optional

from services.platform.runtime.tools.dynamic_api_tool_builder import build_api_tool
from services.platform.runtime.tools.dynamic_knowledge_tool_builder import (
    build_knowledge_tool,
)
from services.platform.runtime.tools.dynamic_script_tool_builder import (
    build_action_only_tool,
    build_script_tool,
)
from services.platform.runtime.tools.dynamic_tool_helpers import (
    _effective_constructor_params,
    _interpolate_template,
    _is_interpolation_value,
    _resolve_runtime_target,
)
from services.platform.runtime.tools.parameter_resolver import (
    to_camel_case as _to_camel_case,
    to_snake_case as _to_snake_case,
)
from services.platform.runtime.tools.tool_name_sanitizer import sanitize_provider_tool_name


class DynamicToolFactory:
    @staticmethod
    def _provider_tool_name(tool_record, preferred_name: Optional[str] = None) -> str:
        return sanitize_provider_tool_name(
            preferred_name,
            getattr(tool_record, "name", None),
            getattr(tool_record, "slug", None),
            f"tool_{getattr(tool_record, 'id', '')}",
        )

    @staticmethod
    def create_tool(
        tool_record,
        actions: List[object],
        *,
        force_direct_response: bool = False,
    ):
        """Build a single Agno-compatible tool from DB config."""
        provider_name = DynamicToolFactory._provider_tool_name(tool_record)

        if tool_record.tool_type == "api":
            return build_api_tool(
                tool_record,
                provider_name=provider_name,
                force_direct_response=force_direct_response,
            )
        if tool_record.tool_type == "knowledge":
            return build_knowledge_tool(
                tool_record,
                provider_name=provider_name,
                force_direct_response=force_direct_response,
            )
        return build_script_tool(
            tool_record,
            actions,
            provider_name=provider_name,
            force_direct_response=force_direct_response,
        )

    @staticmethod
    def create_action_only_tool(
        tool_record,
        actions: List[object],
        cached_result: Optional[str] = None,
        *,
        force_direct_response: bool = False,
    ):
        return build_action_only_tool(
            tool_record,
            actions,
            cached_result,
            provider_name_for=DynamicToolFactory._provider_tool_name,
            force_direct_response=force_direct_response,
        )



__all__ = [
    "DynamicToolFactory",
    "_effective_constructor_params",
    "_interpolate_template",
    "_is_interpolation_value",
    "_resolve_runtime_target",
    "_to_camel_case",
    "_to_snake_case",
]
