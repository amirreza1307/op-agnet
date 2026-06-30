from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Iterable, Optional, Type

log = logging.getLogger(__name__)

from api.errors import NotFoundError
from setup.translator import trans
from api.serializers import serialize_response_value
from database.repositories.main.agent_node_edge_repo import AgentNodeEdgeRepo
from database.repositories.main.agent_channel_repo import AgentChannelRepo
from database.repositories.main.agent_node_mcp_binding_repo import AgentNodeMcpBindingRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from database.repositories.main.agent_node_skill_binding_repo import AgentNodeSkillBindingRepo
from database.repositories.main.agent_node_tool_binding_repo import AgentNodeToolBindingRepo
from database.repositories.main.mcp_server_repo import McpServerRepo
from database.repositories.main.skill_package_repo import SkillPackageRepo
from database.repositories.main.tool_action_binding_repo import ToolActionBindingRepo
from database.repositories.main.tool_action_repo import ToolActionRepo
from database.repositories.main.tool_repo import ToolRepo
from database.schemas.main.agent_node_schema import AgentNodeSchema
from database.schemas.main.mcp_server_schema import McpServerSchema
from database.schemas.main.skill_package_schema import SkillPackageSchema
from database.schemas.main.tool_action_schema import ToolActionSchema
from database.schemas.main.tool_schema import ToolSchema
from services.platform.admin.mcp.mcp_admin_service import MCPAdminService
from services.platform.graph.node_registry_service import NodeRegistryService
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from services.platform.runtime.mcp.mcp_binding_factory import McpBindingFactory
from services.platform.runtime.tools.dynamic_tool_helpers import resolve_effective_tool_parameters
from services.platform.admin.mcp.skill_loader_service import SkillLoaderService
from services.platform.channels.channel_admin_service import ChannelAdminService


class AdminQueryService:
    @staticmethod
    async def get_overview() -> dict[str, Any]:
        await PlatformCacheManager.load()
        traces_enabled = AdminQueryService._traces_enabled_state()

        is_loaded = getattr(
            PlatformCacheManager,
            "is_loaded",
            lambda: PlatformCacheManager._cache_loaded,
        )()

        return {
            "counts": {
                "nodes": len(PlatformCacheManager.nodes_by_id),
                "edges": sum(len(items) for items in PlatformCacheManager.edges_by_parent_id.values()),
                "tools": len(PlatformCacheManager.tools_by_id),
                "mcp_servers": len(PlatformCacheManager.mcp_servers_by_id),
                "skills": len(PlatformCacheManager.skills_by_id),
                "tool_actions": sum(len(items) for items in PlatformCacheManager.actions_by_tool_id.values()),
            },
            "cache": {
                "loaded": is_loaded,
                "global_base_prompt_enabled": False,
            },
            "runtime": {
                "traces_enabled": traces_enabled,
            },
        }

    @staticmethod
    def _traces_enabled_state() -> bool:
        """Best-effort, side-effect-free read of the Agno tracing toggle."""
        try:
            from services.platform.runtime.agno import agno_runtime as _agno_runtime
        except Exception as exc:
            log.debug("platform_admin_query: agno_runtime import failed (%s)", exc)
            return False
        for attr in ("AGNO_TRACING_ENABLED", "_AGNO_TRACING_ENABLED", "tracing_enabled"):
            value = getattr(_agno_runtime, attr, None)
            if isinstance(value, bool):
                return value
        return False

    @staticmethod
    async def health_check_tracing() -> dict[str, Any]:
        try:
            from services.platform.runtime.agno.agno_runtime import ensure_agno_tracing

            enabled = await ensure_agno_tracing()
        except Exception as exc:
            log.debug("platform_admin_query: ensure_agno_tracing failed (%s)", exc)
            return {"ok": False, "traces_enabled": False, "error": str(exc)}
        return {"ok": True, "traces_enabled": bool(enabled)}

    @classmethod
    async def list_nodes(cls, *, include_inactive: bool = False, search: Optional[str] = None) -> list[dict[str, Any]]:
        await PlatformCacheManager.load()
        nodes = await cls._fetch_records(AgentNodeRepo, AgentNodeSchema, include_inactive=include_inactive)
        channels = await AgentChannelRepo.get_all_enabled()
        channel_counts: dict[int, int] = {}
        for channel in channels:
            channel_counts[channel.node_id] = channel_counts.get(channel.node_id, 0) + 1
        edges_by_parent = PlatformCacheManager.edges_by_parent_id
        graph_children = {node_id: len(edges_by_parent.get(node_id, [])) for node_id in PlatformCacheManager.nodes_by_id}
        parent_names_by_child: dict[int, list[str]] = {}

        for edges in edges_by_parent.values():
            for edge in edges:
                parent = PlatformCacheManager.get_node_by_id(edge.parent_node_id)
                if parent is None:
                    continue
                parent_names_by_child.setdefault(edge.child_node_id, []).append(parent.name)

        return [
            cls._serialize(
                node,
                {
                    "child_count": graph_children.get(node.id, 0),
                    "parent_agent_names": parent_names_by_child.get(node.id, []),
                    "tool_binding_count": len(PlatformCacheManager.get_tool_bindings(node.id)),
                    "mcp_binding_count": len(PlatformCacheManager.get_mcp_bindings(node.id)),
                    "skill_binding_count": len(PlatformCacheManager.get_skill_bindings(node.id)),
                    "channel_count": channel_counts.get(node.id, 0),
                },
            )
            for node in cls._filter_search(nodes, search)
        ]

    @classmethod
    async def list_tools(cls, *, include_inactive: bool = False, search: Optional[str] = None) -> list[dict[str, Any]]:
        await PlatformCacheManager.load()
        tools = await cls._fetch_records(ToolRepo, ToolSchema, include_inactive=include_inactive)
        return [
            cls._with_effective_parameters(
                tool,
                cls._serialize(
                    tool,
                    {
                        "action_count": len(PlatformCacheManager.actions_by_tool_id.get(tool.id, [])),
                    },
                ),
            )
            for tool in cls._filter_search(tools, search)
        ]

    @classmethod
    async def list_actions(cls, *, include_inactive: bool = False, search: Optional[str] = None) -> list[dict[str, Any]]:
        actions = await cls._fetch_records(ToolActionRepo, ToolActionSchema, include_inactive=include_inactive)
        return [cls._serialize(action) for action in cls._filter_search(actions, search)]

    @classmethod
    async def list_mcp_servers(cls, *, include_inactive: bool = False, search: Optional[str] = None) -> list[dict[str, Any]]:
        servers = await cls._fetch_records(McpServerRepo, McpServerSchema, include_inactive=include_inactive)
        return [cls._serialize(server, cls._mcp_server_extra(server)) for server in cls._filter_search(servers, search)]

    @classmethod
    async def list_skills(cls, *, include_inactive: bool = False, search: Optional[str] = None) -> list[dict[str, Any]]:
        skills = await cls._fetch_records(SkillPackageRepo, SkillPackageSchema, include_inactive=include_inactive)
        return [cls._serialize(skill) for skill in cls._filter_search(skills, search)]

    @staticmethod
    async def get_catalog() -> dict[str, Any]:
        return {
            "nodes": await AdminQueryService.list_nodes(),
            "tools": await AdminQueryService.list_tools(),
            "actions": await AdminQueryService.list_actions(),
            "mcp_servers": await AdminQueryService.list_mcp_servers(),
            "skills": await AdminQueryService.list_skills(),
        }

    @classmethod
    async def get_node_detail(cls, node_id: int) -> dict[str, Any]:
        await PlatformCacheManager.load()
        node = await cls._find_record_by_id(AgentNodeRepo, AgentNodeSchema, node_id)
        if node is None:
            raise NotFoundError(trans("errors.platform.admin.node_not_found_generic"))

        graph = await NodeRegistryService.get_graph(node)
        child_edges = [
            cls._serialize(
                edge,
                {
                    "child": cls._serialize(PlatformCacheManager.get_node_by_id(edge.child_node_id)),
                },
            )
            for edge in PlatformCacheManager.get_children_edges(node.id)
        ]
        incoming_edges = [
            cls._serialize(
                edge,
                {
                    "parent": cls._serialize(PlatformCacheManager.get_node_by_id(edge.parent_node_id)),
                },
            )
            for edge in await AgentNodeEdgeRepo.get_all_active_edges()
            if edge.child_node_id == node.id
        ]

        tool_bindings = []
        for binding in PlatformCacheManager.get_tool_bindings(node.id):
            tool_bindings.append(
                cls._serialize(
                    binding,
                    {
                        "tool": cls._serialize(PlatformCacheManager.tools_by_id.get(binding.tool_id)),
                    },
                )
            )

        mcp_bindings = []
        for binding in PlatformCacheManager.get_mcp_bindings(node.id):
            mcp_bindings.append(
                cls._serialize(
                    binding,
                    {
                        "mcp_server": cls._serialize(PlatformCacheManager.mcp_servers_by_id.get(binding.mcp_server_id)),
                    },
                )
            )

        skill_bindings = []
        for binding in PlatformCacheManager.get_skill_bindings(node.id):
            skill_bindings.append(
                cls._serialize(
                    binding,
                    {
                        "skill_package": cls._serialize(PlatformCacheManager.skills_by_id.get(binding.skill_package_id)),
                    },
                )
            )

        channels = [
            ChannelAdminService.serialize(channel)
            for channel in await AgentChannelRepo.list_by_node_id(node.id)
        ]

        return {
            "node": cls._serialize(node),
            "graph": graph,
            "children": child_edges,
            "parents": incoming_edges,
            "tool_bindings": tool_bindings,
            "mcp_bindings": mcp_bindings,
            "skill_bindings": skill_bindings,
            "channels": channels,
        }

    @classmethod
    async def get_tool_detail(cls, tool_id: int) -> dict[str, Any]:
        await PlatformCacheManager.load()
        tool = await cls._find_record_by_id(ToolRepo, ToolSchema, tool_id)
        if tool is None:
            raise NotFoundError(trans("errors.platform.admin.tool_not_found_generic"))

        bindings = await ToolActionBindingRepo.get_bindings_by_tool_id(tool_id)
        node_bindings = await AgentNodeToolBindingRepo.get_all_active_bindings()
        bound_nodes = [
            cls._serialize(
                binding,
                {
                    "node": cls._serialize(PlatformCacheManager.get_node_by_id(binding.node_id)),
                },
            )
            for binding in node_bindings
            if binding.tool_id == tool_id
        ]
        actions = []
        for binding in bindings:
            action = await cls._find_record_by_id(ToolActionRepo, ToolActionSchema, binding.action_id)
            actions.append(cls._serialize(binding, {"action": cls._serialize(action)}))
        return {
            "tool": cls._with_effective_parameters(tool, cls._serialize(tool)),
            "action_bindings": actions,
            "node_bindings": bound_nodes,
        }

    @classmethod
    async def get_action_detail(cls, action_id: int) -> dict[str, Any]:
        action = await cls._find_record_by_id(ToolActionRepo, ToolActionSchema, action_id)
        if action is None:
            raise NotFoundError(trans("errors.platform.admin.action_not_found_generic"))
        bindings = await ToolActionBindingRepo.get_all_active_bindings()
        attached_tools = []
        for binding in bindings:
            if binding.action_id != action_id:
                continue
            tool = await cls._find_record_by_id(ToolRepo, ToolSchema, binding.tool_id)
            attached_tools.append(cls._serialize(binding, {"tool": cls._serialize(tool)}))
        return {"action": cls._serialize(action), "tool_bindings": attached_tools}

    @classmethod
    async def get_mcp_server_detail(cls, server_id: int) -> dict[str, Any]:
        server = await cls._find_record_by_id(McpServerRepo, McpServerSchema, server_id)
        if server is None:
            raise NotFoundError(trans("errors.platform.admin.mcp_server_not_found_generic"))
        bindings = await AgentNodeMcpBindingRepo.get_all_active_bindings()
        attached_nodes = []
        for binding in bindings:
            if binding.mcp_server_id != server_id:
                continue
            node = await cls._find_record_by_id(AgentNodeRepo, AgentNodeSchema, binding.node_id)
            attached_nodes.append(cls._serialize(binding, {"node": cls._serialize(node)}))
        return {"mcp_server": cls._serialize(server, cls._mcp_server_extra(server)), "node_bindings": attached_nodes}

    @classmethod
    async def get_skill_detail(cls, skill_id: int) -> dict[str, Any]:
        skill = await cls._find_record_by_id(SkillPackageRepo, SkillPackageSchema, skill_id)
        if skill is None:
            raise NotFoundError(trans("errors.platform.admin.skill_package_not_found_generic"))
        bindings = await AgentNodeSkillBindingRepo.get_all_active_bindings()
        attached_nodes = []
        for binding in bindings:
            if binding.skill_package_id != skill_id:
                continue
            node = await cls._find_record_by_id(AgentNodeRepo, AgentNodeSchema, binding.node_id)
            attached_nodes.append(cls._serialize(binding, {"node": cls._serialize(node)}))
        resolved_path = str(SkillLoaderService.resolve_source_path(skill.source_path))
        return {
            "skill_package": cls._serialize(skill),
            "resolved_source_path": resolved_path,
            "node_bindings": attached_nodes,
        }

    @staticmethod
    async def test_mcp_server(server_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        server = await AdminQueryService._find_record_by_id(McpServerRepo, McpServerSchema, server_id)
        if server is None:
            raise NotFoundError(trans("errors.platform.admin.mcp_server_not_found_generic"))

        binding = SimpleNamespace(
            header_template_json=payload.get("header_template_json") or {},
            session_state=payload.get("session_state") or {},
        )
        try:
            created = McpBindingFactory.create(server, binding)
            tool_count = 0
            sample_tools: list[dict[str, Any]] = []
            sample_result_json: dict[str, Any] | None = None

            async with created as live_tools:
                if live_tools.session is None:
                    raise RuntimeError(trans("errors.platform.admin.mcp_session_init_failed"))

                available_tools = await live_tools.session.list_tools()  # type: ignore[attr-defined]
                sample_tools = [
                    {
                        "name": tool.name,
                        "description": getattr(tool, "description", None),
                        "input_schema": getattr(tool, "inputSchema", None),
                    }
                    for tool in available_tools.tools[:5]
                ]
                tool_count = len(available_tools.tools)
                sample_result_json = {
                    "tools": sample_tools,
                }

            return {
                "ok": True,
                "transport": server.transport,
                "tool_count": tool_count,
                "sample_tools": sample_tools,
                "sample_result_json": sample_result_json,
                "resolved_working_directory": (
                    str(McpBindingFactory._resolve_working_directory(server))
                    if server.transport == "stdio"
                    else None
                ),
                "tool_wrapper_type": created.__class__.__name__,
                "message": f"MCP connected successfully and exposed {tool_count} tool(s)",
            }
        except Exception as exc:
            return {
                "ok": False,
                "transport": server.transport,
                "tool_count": 0,
                "sample_tools": [],
                "sample_result_json": None,
                "message": str(exc),
            }

    @staticmethod
    def validate_skill_source_path(source_path: str) -> dict[str, Any]:
        resolved = SkillLoaderService.resolve_source_path(source_path)
        return {
            "ok": True,
            "source_path": source_path,
            "resolved_path": str(resolved),
            "exists": resolved.exists(),
            "is_directory": resolved.is_dir(),
        }

    @staticmethod
    async def _fetch_records(repo, schema, *, include_inactive: bool = False) -> list[Any]:
        query = repo.select_query().select("*")
        results = await repo.get(query)
        records = results if results else []
        if include_inactive:
            return records
        return [record for record in records if getattr(record, schema.IS_ACTIVE, True)]

    @staticmethod
    async def _find_record_by_id(repo, schema, record_id: int) -> Any:
        query = repo.select_query().where(repo.field(schema.ID).eq(record_id)).select("*")
        return await repo.first(query)

    @staticmethod
    def _filter_search(records: Iterable[Any], search: Optional[str]) -> list[Any]:
        if not search:
            return list(records)
        needle = search.strip().lower()
        if not needle:
            return list(records)
        return [record for record in records if AdminQueryService._matches_search(record, needle)]

    @staticmethod
    def _matches_search(record: Any, needle: str) -> bool:
        fields = [
            getattr(record, "slug", None),
            getattr(record, "name", None),
            getattr(record, "title", None),
            getattr(record, "description", None),
            getattr(record, "system_prompt", None),
            getattr(record, "source_path", None),
            getattr(record, "entrypoint", None),
            getattr(record, "transport", None),
            getattr(record, "url", None),
        ]
        return any(isinstance(value, str) and needle in value.lower() for value in fields)

    @staticmethod
    def _serialize(value: Any, extra: Optional[dict[str, Any]] = None) -> Any:
        data = serialize_response_value(value)
        if extra:
            data.update(serialize_response_value(extra))
        return data

    @staticmethod
    def _with_effective_parameters(tool: Any, data: dict[str, Any]) -> dict[str, Any]:
        """Replace ``parameters`` in a serialized tool dict with Input-derived
        params for ``script`` tools; leave other tool types untouched.

        Requires ``PlatformCacheManager.load()`` to have run (callers already
        await it) so action slugs are available via ``actions_by_tool_id``.
        """
        if getattr(tool, "tool_type", None) != "script":
            return data
        slugs = [a.slug for a in PlatformCacheManager.actions_by_tool_id.get(tool.id, [])]
        data["parameters"] = resolve_effective_tool_parameters(
            tool_type=tool.tool_type,
            db_parameters=tool.parameters,
            action_slugs=slugs,
            metadata_json=getattr(tool, "metadata_json", None),
        )
        return data

    @staticmethod
    def _mcp_server_extra(server: Any) -> dict[str, Any]:
        local_meta = MCPAdminService.get_local_mcp_metadata(server)
        if not local_meta:
            return {}
        return {
            "local_source_path": local_meta.get("source_path"),
            "local_entrypoint": local_meta.get("entrypoint"),
        }
