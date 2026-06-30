"""Facade preserving the historical ``ToolAdminService`` import surface.

The implementation has moved to:
- :mod:`services.platform.admin.tools.tool_admin` (``ToolAdmin``)
- :mod:`services.platform.admin.tools.script_discovery` (``ScriptDiscovery``)
- :mod:`services.platform.admin.tools.tool_actions_resolver`
- :mod:`services.platform.admin.tools.tool_schemas` (``ToolUpdateSchema``)

This shim re-exports those entrypoints under the legacy ``ToolAdminService``
classname so existing controllers/callers keep compiling.
"""
from __future__ import annotations

from typing import Any

from services.platform.admin.tools.script_discovery import ScriptDiscovery
from services.platform.admin.tools.tool_actions_resolver import (
    resolve_tool_actions_payload,
)
from services.platform.admin.tools.tool_admin import ToolAdmin


class ToolAdminService:
    """Thin facade delegating to ``ToolAdmin`` and the discovery helpers."""

    @staticmethod
    async def list_tools() -> list[Any]:
        return await ToolAdmin.list_tools()

    @staticmethod
    async def list_actions() -> list[Any]:
        return await ToolAdmin.list_actions()

    @staticmethod
    async def create_tool(payload: dict) -> Any:
        return await ToolAdmin.create_tool(payload)

    @staticmethod
    async def update_tool(tool_id: int, payload: dict) -> Any:
        return await ToolAdmin.update_tool(tool_id, payload)

    @staticmethod
    def list_tool_scripts() -> dict[str, Any]:
        return ScriptDiscovery.list_tool_scripts()

    @staticmethod
    async def deactivate_tool(tool_id: int) -> Any:
        return await ToolAdmin.deactivate_tool(tool_id)

    @staticmethod
    async def create_action(payload: dict) -> Any:
        return await ToolAdmin.create_action(payload)

    @staticmethod
    async def update_action(action_id: int, payload: dict) -> Any:
        return await ToolAdmin.update_action(action_id, payload)

    @staticmethod
    async def deactivate_action(action_id: int) -> Any:
        return await ToolAdmin.deactivate_action(action_id)

    @staticmethod
    async def bind_tool(node_id: int, payload: dict) -> Any:
        return await ToolAdmin.bind_tool(node_id, payload)

    @staticmethod
    async def unbind_tool(binding_id: int) -> Any:
        return await ToolAdmin.unbind_tool(binding_id)

    @staticmethod
    async def bind_action(tool_id: int, payload: dict) -> Any:
        return await ToolAdmin.bind_action(tool_id, payload)

    @staticmethod
    async def unbind_action(binding_id: int) -> Any:
        return await ToolAdmin.unbind_action(binding_id)

    # ----- Legacy private helpers used by other admin services --------------

    @staticmethod
    async def _replace_tool_actions(tool_id: int, actions_payload) -> None:
        return await ToolAdmin._replace_tool_actions(tool_id, actions_payload)

    @staticmethod
    async def _create_inline_action_binding(tool_id: int, action_payload: dict) -> Any:
        return await ToolAdmin._create_inline_action_binding(tool_id, action_payload)

    @staticmethod
    async def _resolve_tool_actions_payload(payload: dict[str, Any]):
        return await resolve_tool_actions_payload(payload)
