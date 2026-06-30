"""Facade preserving the historical ``MCPAdminService`` import surface.

The implementation has been decomposed into:
- :mod:`services.platform.admin.mcp.mcp_server_admin` (``McpServerAdmin``)
- :mod:`services.platform.admin.mcp.skill_package_admin` (``SkillPackageAdmin``)
- :mod:`services.platform.admin.mcp.local_mcp_discovery` (``LocalMcpDiscovery``)
- :mod:`services.platform.admin.mcp.mcp_payload_validator`
- :mod:`services.platform.admin.mcp.mcp_path_security`

This module re-exports those entrypoints under the legacy ``MCPAdminService``
classname so existing controllers/callers keep compiling.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from services.platform.admin.mcp.local_mcp_discovery import LocalMcpDiscovery
from services.platform.admin.mcp.mcp_path_security import (
    ensure_mcp_working_directory,
    resolve_mcp_working_directory,
)
from services.platform.admin.mcp.mcp_payload_validator import (
    normalize_remote_mcp_url,
    validate_mcp_payload,
)
from services.platform.admin.mcp.mcp_server_admin import McpServerAdmin
from services.platform.admin.mcp.skill_package_admin import SkillPackageAdmin


class MCPAdminService:
    """Thin facade that delegates to the decomposed admin classes."""

    _LOCAL_MCP_METADATA_KEY = LocalMcpDiscovery.LOCAL_MCP_METADATA_KEY
    _LOCAL_MCP_ENTRYPOINT = LocalMcpDiscovery.LOCAL_MCP_ENTRYPOINT

    # ----- MCP servers ------------------------------------------------------

    @staticmethod
    async def list_mcp_servers() -> list[Any]:
        return await McpServerAdmin.list_mcp_servers()

    @staticmethod
    async def create_mcp_server(payload: dict) -> Any:
        return await McpServerAdmin.create_mcp_server(payload)

    @staticmethod
    async def update_mcp_server(server_id: int, payload: dict) -> Any:
        return await McpServerAdmin.update_mcp_server(server_id, payload)

    @staticmethod
    async def deactivate_mcp_server(server_id: int) -> Any:
        return await McpServerAdmin.deactivate_mcp_server(server_id)

    @staticmethod
    async def bind_mcp(node_id: int, payload: dict) -> Any:
        return await McpServerAdmin.bind_mcp(node_id, payload)

    @staticmethod
    async def unbind_mcp(binding_id: int) -> Any:
        return await McpServerAdmin.unbind_mcp(binding_id)

    # ----- Skill packages ---------------------------------------------------

    @staticmethod
    async def list_skills() -> list[Any]:
        return await SkillPackageAdmin.list_skills()

    @staticmethod
    async def create_skill(payload: dict) -> Any:
        return await SkillPackageAdmin.create_skill(payload)

    @staticmethod
    async def update_skill(skill_id: int, payload: dict) -> Any:
        return await SkillPackageAdmin.update_skill(skill_id, payload)

    @staticmethod
    async def bind_skill(node_id: int, payload: dict) -> Any:
        return await SkillPackageAdmin.bind_skill(node_id, payload)

    @staticmethod
    async def unbind_skill(binding_id: int) -> Any:
        return await SkillPackageAdmin.unbind_skill(binding_id)

    @staticmethod
    async def deactivate_skill(skill_id: int) -> Any:
        return await SkillPackageAdmin.deactivate_skill(skill_id)

    # ----- Local MCP discovery ---------------------------------------------

    @staticmethod
    def list_local_mcp_sources() -> dict[str, Any]:
        return LocalMcpDiscovery.list_local_mcp_sources()

    @staticmethod
    async def sync_local_mcp_servers() -> None:
        await LocalMcpDiscovery.sync_local_mcp_servers()

    @staticmethod
    def get_local_mcp_metadata(server: Any) -> Optional[dict[str, Any]]:
        return LocalMcpDiscovery.get_local_mcp_metadata(server)

    # ----- Lower-level helpers exposed for legacy callers ------------------

    @staticmethod
    def _validate_mcp_payload(payload: dict) -> None:
        validate_mcp_payload(payload)

    @staticmethod
    def _normalize_remote_mcp_url(transport: Optional[str], url: Optional[str]) -> Optional[str]:
        return normalize_remote_mcp_url(transport, url)

    @staticmethod
    def _resolve_mcp_working_directory(working_directory: Optional[str]) -> str:
        return resolve_mcp_working_directory(working_directory)

    @staticmethod
    def _ensure_mcp_working_directory(working_directory: Optional[str]) -> str:
        return ensure_mcp_working_directory(working_directory)

    @staticmethod
    def _prepare_mcp_payload(payload: dict[str, Any], existing_server: Any | None = None) -> dict[str, Any]:
        return McpServerAdmin._prepare_mcp_payload(payload, existing_server=existing_server)

    @staticmethod
    def _build_local_mcp_configuration(source_path: str) -> dict[str, str]:
        return LocalMcpDiscovery.build_local_mcp_configuration(source_path)

    @staticmethod
    def _resolve_local_mcp_source_directory(source_path: str) -> Path:
        return LocalMcpDiscovery.resolve_local_mcp_source_directory(source_path)

    @staticmethod
    def _merge_local_mcp_metadata(
        metadata_json: Optional[dict[str, Any]],
        *,
        source_path: str,
        entrypoint: str,
    ) -> dict[str, Any]:
        return LocalMcpDiscovery.merge_local_mcp_metadata(
            metadata_json, source_path=source_path, entrypoint=entrypoint
        )

    @staticmethod
    def _strip_local_mcp_metadata(metadata_json: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        return LocalMcpDiscovery.strip_local_mcp_metadata(metadata_json)

    @staticmethod
    def _slugify_mcp_source(source_path: str) -> str:
        return LocalMcpDiscovery.slugify_mcp_source(source_path)

    @staticmethod
    def _extract_local_mcp_display_name(entrypoint: Path, fallback_name: str) -> str:
        return LocalMcpDiscovery.extract_local_mcp_display_name(entrypoint, fallback_name)

    @staticmethod
    def _format_mcp_display_name(raw_name: str) -> str:
        return LocalMcpDiscovery.format_mcp_display_name(raw_name)

    @staticmethod
    def _normalize_skill_source_path(source_path: str) -> str:
        return SkillPackageAdmin._normalize_skill_source_path(source_path)
