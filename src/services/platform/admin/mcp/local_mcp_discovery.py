"""Filesystem discovery + AST parsing for local MCP servers."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Optional

from api.errors import BadRequestError
from database.repositories.main.mcp_server_repo import McpServerRepo
from services.platform.admin._shared import normalize_payload
from services.platform.admin.mcp.mcp_path_security import resolve_mcp_working_directory
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.config import config
from setup.translator import trans


_LOCAL_MCP_METADATA_KEY = "local_mcp"
_LOCAL_MCP_ENTRYPOINT = "server.py"


class LocalMcpDiscovery:
    LOCAL_MCP_METADATA_KEY = _LOCAL_MCP_METADATA_KEY
    LOCAL_MCP_ENTRYPOINT = _LOCAL_MCP_ENTRYPOINT

    @staticmethod
    def list_local_mcp_sources() -> dict[str, Any]:
        root_dir = config.mcp_root_dir
        items: list[dict[str, Any]] = []
        if root_dir.is_dir():
            for source_dir in sorted(root_dir.iterdir()):
                if not source_dir.is_dir() or source_dir.name.startswith("_") or source_dir.name.startswith("."):
                    continue

                entrypoint = source_dir / _LOCAL_MCP_ENTRYPOINT
                if not entrypoint.is_file():
                    continue

                source_path = str(source_dir.relative_to(root_dir)).replace("\\", "/")
                items.append(
                    {
                        "source_path": source_path,
                        "slug": LocalMcpDiscovery.slugify_mcp_source(source_path),
                        "display_name": LocalMcpDiscovery.extract_local_mcp_display_name(
                            entrypoint, source_dir.name
                        ),
                        "entrypoint": _LOCAL_MCP_ENTRYPOINT,
                        "command": f"python {_LOCAL_MCP_ENTRYPOINT}",
                        "working_directory": source_path,
                    }
                )

        return {
            "items": items,
            "mcp_root_dir": str(root_dir),
        }

    @staticmethod
    async def sync_local_mcp_servers() -> None:
        discovered = LocalMcpDiscovery.list_local_mcp_sources()
        source_items = discovered.get("items", [])
        active_servers = await McpServerRepo.get_all_active_servers()
        active_by_source: dict[str, Any] = {}
        seen_sources: set[str] = set()
        changed = False

        for server in active_servers:
            local_meta = LocalMcpDiscovery.get_local_mcp_metadata(server)
            if not local_meta:
                continue
            source_path = str(local_meta.get("source_path") or "").strip()
            if source_path:
                active_by_source[source_path] = server

        for item in source_items:
            source_path = item["source_path"]
            seen_sources.add(source_path)
            existing = active_by_source.get(source_path)
            metadata_json = LocalMcpDiscovery.merge_local_mcp_metadata(
                getattr(existing, "metadata_json", None),
                source_path=source_path,
                entrypoint=item["entrypoint"],
            )

            if existing is None:
                slug_conflict = await McpServerRepo.find_active_by_slug(item["slug"])
                if slug_conflict is not None:
                    continue

                await McpServerRepo.create_return(
                    normalize_payload(
                        "mcp_server",
                        {
                            "slug": item["slug"],
                            "name": item["display_name"],
                            "transport": "stdio",
                            "command": item["command"],
                            "working_directory": item["working_directory"],
                            "timeout_seconds": config.MCP_DEFAULT_TIMEOUT_SECONDS,
                            "refresh_connection": False,
                            "allow_partial_failure": False,
                            "is_active": True,
                            "metadata_json": metadata_json,
                        },
                    )
                )
                changed = True
                continue

            update_payload: dict[str, Any] = {}
            if existing.transport != "stdio":
                update_payload["transport"] = "stdio"
            if existing.command != item["command"]:
                update_payload["command"] = item["command"]
            if existing.working_directory != item["working_directory"]:
                update_payload["working_directory"] = item["working_directory"]
            if (existing.metadata_json or None) != (metadata_json or None):
                update_payload["metadata_json"] = metadata_json

            if update_payload:
                await McpServerRepo.update_by_id(
                    existing.id,
                    normalize_payload("mcp_server", update_payload),
                    return_=False,
                )
                changed = True

        for server in active_servers:
            local_meta = LocalMcpDiscovery.get_local_mcp_metadata(server)
            if not local_meta:
                continue
            source_path = str(local_meta.get("source_path") or "").strip()
            if source_path and source_path not in seen_sources:
                await McpServerRepo.update_by_id(server.id, {"is_active": False}, return_=False)
                changed = True

        if changed:
            await PlatformCacheManager.refresh()

    @staticmethod
    def get_local_mcp_metadata(server: Any) -> Optional[dict[str, Any]]:
        metadata = getattr(server, "metadata_json", None)
        if isinstance(metadata, dict):
            local_meta = metadata.get(_LOCAL_MCP_METADATA_KEY)
            if isinstance(local_meta, dict) and local_meta.get("source_path"):
                return local_meta

        if getattr(server, "transport", None) != "stdio":
            return None

        working_directory = str(getattr(server, "working_directory", "") or "").strip()
        command = str(getattr(server, "command", "") or "").strip()
        if not working_directory or command != f"python {_LOCAL_MCP_ENTRYPOINT}":
            return None

        source_dir = config.mcp_root_dir / working_directory
        entrypoint = source_dir / _LOCAL_MCP_ENTRYPOINT
        if not entrypoint.is_file():
            return None

        return {
            "managed": True,
            "source_path": working_directory.replace("\\", "/"),
            "entrypoint": _LOCAL_MCP_ENTRYPOINT,
        }

    @staticmethod
    def merge_local_mcp_metadata(
        metadata_json: Optional[dict[str, Any]],
        *,
        source_path: str,
        entrypoint: str,
    ) -> dict[str, Any]:
        metadata = dict(metadata_json or {})
        metadata[_LOCAL_MCP_METADATA_KEY] = {
            "managed": True,
            "source_path": source_path,
            "entrypoint": entrypoint,
        }
        return metadata

    @staticmethod
    def strip_local_mcp_metadata(metadata_json: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if not isinstance(metadata_json, dict):
            return metadata_json
        metadata = dict(metadata_json)
        metadata.pop(_LOCAL_MCP_METADATA_KEY, None)
        return metadata or None

    @staticmethod
    def slugify_mcp_source(source_path: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", source_path).strip("-").lower()
        if not slug:
            raise BadRequestError(trans("errors.platform.admin.local_mcp_slug_derivation_failed"))
        return slug

    @staticmethod
    def build_local_mcp_configuration(source_path: str) -> dict[str, str]:
        source_dir = LocalMcpDiscovery.resolve_local_mcp_source_directory(source_path)
        normalized_source_path = str(source_dir.relative_to(config.mcp_root_dir)).replace("\\", "/")
        return {
            "source_path": normalized_source_path,
            "entrypoint": _LOCAL_MCP_ENTRYPOINT,
            "command": f"python {_LOCAL_MCP_ENTRYPOINT}",
            "working_directory": normalized_source_path,
        }

    @staticmethod
    def resolve_local_mcp_source_directory(source_path: str) -> Path:
        requested = (source_path or "").strip()
        if not requested:
            raise BadRequestError(trans("errors.platform.admin.local_mcp_source_path_required"))

        root_dir = config.mcp_root_dir.resolve()
        candidate = Path(requested)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (root_dir / candidate).resolve()

        if root_dir not in {resolved, *resolved.parents}:
            raise BadRequestError(trans("errors.platform.admin.local_mcp_source_path_outside_root", root_dir=root_dir))
        if not resolved.is_dir():
            raise BadRequestError(trans("errors.platform.admin.local_mcp_source_path_not_directory"))

        entrypoint = resolved / _LOCAL_MCP_ENTRYPOINT
        if not entrypoint.is_file():
            raise BadRequestError(
                trans("errors.platform.admin.local_mcp_missing_entrypoint", entrypoint=_LOCAL_MCP_ENTRYPOINT)
            )

        return resolved

    @staticmethod
    def extract_local_mcp_display_name(entrypoint: Path, fallback_name: str) -> str:
        """Parse `entrypoint` and return the first FastMCP("...") or FastMCP(name="...") literal.

        Supports both positional first-arg and keyword ``name=`` forms.
        """
        try:
            tree = ast.parse(entrypoint.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            return LocalMcpDiscovery.format_mcp_display_name(fallback_name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func
            is_fast_mcp_call = isinstance(func, ast.Name) and func.id == "FastMCP"
            if not is_fast_mcp_call:
                continue

            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return node.args[0].value.strip() or LocalMcpDiscovery.format_mcp_display_name(fallback_name)

            for kw in node.keywords or []:
                if (
                    kw.arg == "name"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)
                ):
                    return kw.value.value.strip() or LocalMcpDiscovery.format_mcp_display_name(fallback_name)

        return LocalMcpDiscovery.format_mcp_display_name(fallback_name)

    @staticmethod
    def format_mcp_display_name(raw_name: str) -> str:
        cleaned = raw_name.replace("-", " ").replace("_", " ").strip()
        return cleaned.title() if cleaned else "Local MCP"

    @staticmethod
    def ensure_mcp_working_directory(working_directory: Optional[str]) -> str:
        # Local re-export to keep the discovery class self-contained.
        from services.platform.admin.mcp.mcp_path_security import ensure_mcp_working_directory as _ensure

        return _ensure(working_directory)
