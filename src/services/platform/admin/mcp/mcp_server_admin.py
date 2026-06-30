"""CRUD + binding admin for MCP servers."""
from __future__ import annotations

from typing import Any

from api.errors import ConflictError, NotFoundError
from database.repositories.main.agent_node_mcp_binding_repo import AgentNodeMcpBindingRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from database.repositories.main.mcp_server_repo import McpServerRepo
from services.platform.admin._shared import normalize_payload
from services.platform.admin.mcp.local_mcp_discovery import LocalMcpDiscovery
from services.platform.admin.mcp.mcp_path_security import ensure_mcp_working_directory
from services.platform.admin.mcp.mcp_payload_validator import (
    normalize_remote_mcp_url,
    validate_mcp_payload,
)
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.translator import trans


class McpServerAdmin:
    @staticmethod
    async def list_mcp_servers() -> list[Any]:
        return await McpServerRepo.get_all_active_servers()

    @staticmethod
    async def create_mcp_server(payload: dict) -> Any:
        existing = await McpServerRepo.find_active_by_slug(payload["slug"])
        if existing:
            raise ConflictError(trans("errors.platform.admin.mcp_server_slug_exists", slug=payload["slug"]))
        payload = McpServerAdmin._prepare_mcp_payload(payload)
        validate_mcp_payload(payload)
        if payload.get("transport") == "stdio":
            ensure_mcp_working_directory(payload.get("working_directory"))
        result = await McpServerRepo.create_return(normalize_payload("mcp_server", payload))
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def update_mcp_server(server_id: int, payload: dict) -> Any:
        if "slug" in payload:
            existing = await McpServerRepo.find_active_by_slug(payload["slug"])
            if existing and existing.id != server_id:
                raise ConflictError(trans("errors.platform.admin.mcp_server_slug_exists", slug=payload["slug"]))
        existing_server = await McpServerRepo.find_active_by_id(server_id)
        if existing_server is None:
            raise NotFoundError(trans("errors.platform.admin.mcp_server_not_found_generic"))

        prepared = McpServerAdmin._prepare_mcp_payload(payload, existing_server=existing_server)

        # Build the fully-resolved view used for validation, then fold its
        # transport-defaulted keys back into the prepared payload so that the
        # SAME normalized dict is what we both validate and persist.
        final_payload = {
            "transport": prepared.get("transport", existing_server.transport),
            "command": prepared.get("command", existing_server.command),
            "url": prepared.get("url", existing_server.url),
            "working_directory": prepared.get("working_directory", existing_server.working_directory),
        }
        validate_mcp_payload(final_payload)
        if final_payload.get("transport") == "stdio":
            ensure_mcp_working_directory(final_payload.get("working_directory"))

        # Ensure transport-derived defaults from `final_payload` are reflected
        # in the actual DB write when the caller did NOT supply them — this
        # closes the A-01 divergence bug where validate ran on one shape and
        # update wrote a different one.
        for key in ("transport", "command", "url", "working_directory"):
            if key not in prepared:
                continue
            prepared[key] = final_payload[key]

        normalized = normalize_payload("mcp_server", prepared)
        if normalized:
            result = await McpServerRepo.update_by_id(server_id, normalized, return_=True)
        else:
            result = existing_server
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def deactivate_mcp_server(server_id: int) -> Any:
        server = await McpServerRepo.find_active_by_id(server_id)
        if server is None:
            raise NotFoundError(trans("errors.platform.admin.mcp_server_not_found", server_id=server_id))
        result = await McpServerRepo.update_by_id(server_id, {"is_active": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def bind_mcp(node_id: int, payload: dict) -> Any:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        server = await McpServerRepo.find_active_by_id(payload["mcp_server_id"])
        if node is None or server is None:
            raise NotFoundError(trans("errors.platform.admin.node_and_mcp_server_required"))
        result = await AgentNodeMcpBindingRepo.create_return(
            normalize_payload(
                "node_mcp_binding",
                {
                    "node_id": node_id,
                    "mcp_server_id": payload["mcp_server_id"],
                    "priority": payload.get("priority", 0),
                    "is_enabled": payload.get("is_enabled", True),
                    "binding_mode": payload.get("binding_mode"),
                    "header_template_json": payload.get("header_template_json"),
                    "metadata_json": payload.get("metadata_json"),
                },
            )
        )
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def unbind_mcp(binding_id: int) -> Any:
        result = await AgentNodeMcpBindingRepo.update_by_id(binding_id, {"is_enabled": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    def _prepare_mcp_payload(payload: dict[str, Any], existing_server: Any | None = None) -> dict[str, Any]:
        normalized_payload = dict(payload)
        local_source_path = normalized_payload.pop("local_source_path", None)

        if local_source_path:
            local_config = LocalMcpDiscovery.build_local_mcp_configuration(local_source_path)
            normalized_payload["transport"] = "stdio"
            normalized_payload["command"] = local_config["command"]
            normalized_payload["working_directory"] = local_config["working_directory"]
            normalized_payload["url"] = None
            normalized_payload["metadata_json"] = LocalMcpDiscovery.merge_local_mcp_metadata(
                normalized_payload.get("metadata_json", getattr(existing_server, "metadata_json", None)),
                source_path=local_config["source_path"],
                entrypoint=local_config["entrypoint"],
            )
            return normalized_payload

        transport = normalized_payload.get("transport", getattr(existing_server, "transport", None))
        if transport in {"sse", "streamable-http"}:
            normalized_payload["command"] = None
            normalized_payload["working_directory"] = None
            normalized_payload["url"] = normalize_remote_mcp_url(
                transport,
                normalized_payload.get("url", getattr(existing_server, "url", None)),
            )
            normalized_payload["metadata_json"] = LocalMcpDiscovery.strip_local_mcp_metadata(
                normalized_payload.get("metadata_json", getattr(existing_server, "metadata_json", None))
            )
            return normalized_payload

        if transport == "stdio" and (
            "command" in normalized_payload
            or "working_directory" in normalized_payload
            or LocalMcpDiscovery.get_local_mcp_metadata(existing_server) is not None
        ):
            normalized_payload["metadata_json"] = LocalMcpDiscovery.strip_local_mcp_metadata(
                normalized_payload.get("metadata_json", getattr(existing_server, "metadata_json", None))
            )

        return normalized_payload
