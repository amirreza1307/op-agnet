import asyncio
import logging
from collections import defaultdict
from types import SimpleNamespace
from typing import Any, Iterable, Optional

from database.models.main.agent_node import AgentNode
from database.models.main.agent_node_edge import AgentNodeEdge
from database.models.main.agent_node_mcp_binding import AgentNodeMcpBinding
from database.models.main.agent_node_skill_binding import AgentNodeSkillBinding
from database.models.main.agent_node_tool_binding import AgentNodeToolBinding
from database.models.main.mcp_server import McpServer
from database.models.main.skill_package import SkillPackage
from database.models.main.tool import Tool
from database.models.main.tool_action import ToolAction
from database.repositories.main.agent_node_edge_repo import AgentNodeEdgeRepo
from database.repositories.main.agent_node_mcp_binding_repo import AgentNodeMcpBindingRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from database.repositories.main.agent_node_skill_binding_repo import AgentNodeSkillBindingRepo
from database.repositories.main.agent_node_tool_binding_repo import AgentNodeToolBindingRepo
from database.repositories.main.mcp_server_repo import McpServerRepo
from database.repositories.main.skill_package_repo import SkillPackageRepo
from database.repositories.main.tool_action_binding_repo import ToolActionBindingRepo
from database.repositories.main.tool_action_repo import ToolActionRepo
from services.platform.admin.tools.tool_cache_service import ToolCacheService
from services.platform.graph.graph_snapshot import GraphSnapshot

logger = logging.getLogger(__name__)


class PlatformCacheManager:
    _cache_loaded: bool = False
    _snapshot: GraphSnapshot = GraphSnapshot.empty()
    _rebuild_lock = asyncio.Lock()

    nodes_by_id: dict[int, AgentNode] = {}
    nodes_by_slug: dict[str, AgentNode] = {}
    edges_by_parent_id: dict[int, list[AgentNodeEdge]] = {}
    tool_bindings_by_node_id: dict[int, list[AgentNodeToolBinding]] = {}
    mcp_bindings_by_node_id: dict[int, list[AgentNodeMcpBinding]] = {}
    skill_bindings_by_node_id: dict[int, list[AgentNodeSkillBinding]] = {}
    tools_by_id: dict[int, Tool] = {}
    tools_by_name: dict[str, Tool] = {}
    actions_by_tool_id: dict[int, list[object]] = {}
    mcp_servers_by_id: dict[int, McpServer] = {}
    skills_by_id: dict[int, SkillPackage] = {}

    @classmethod
    async def load(cls):
        """Build the process-local snapshot from the database."""
        if cls._cache_loaded:
            return
        async with cls._rebuild_lock:
            if cls._cache_loaded:
                return
            await cls._build_cache()
            cls._cache_loaded = True

    @classmethod
    async def refresh(cls):
        async with cls._rebuild_lock:
            await ToolCacheService.invalidate_tools_cache()
            await cls._build_cache()
            cls._cache_loaded = True

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._cache_loaded

    @classmethod
    async def current_snapshot(cls) -> GraphSnapshot:
        await cls.load()
        return cls._snapshot

    # ------------------------------------------------------------------
    # Cache build pipeline (decomposed from a single 120-line method).
    # ------------------------------------------------------------------

    @classmethod
    async def _fetch_raw_data(cls) -> dict[str, Any]:
        return {
            "nodes": await AgentNodeRepo.get_all_active_nodes(),
            "edges": await AgentNodeEdgeRepo.get_all_active_edges(),
            "tool_bindings": await AgentNodeToolBindingRepo.get_all_active_bindings(),
            "mcp_bindings": await AgentNodeMcpBindingRepo.get_all_active_bindings(),
            "skill_bindings": await AgentNodeSkillBindingRepo.get_all_active_bindings(),
            "tools": await ToolCacheService.list_tools(),
            "action_definitions": await ToolActionRepo.get_all_active_actions(),
            "action_bindings": await ToolActionBindingRepo.get_all_active_bindings(),
            "mcp_servers": await McpServerRepo.get_all_active_servers(),
            "skills": await SkillPackageRepo.get_all_active_skills(),
        }

    @classmethod
    def _index_actions(
        cls,
        tools: Iterable[Tool],
        raw_action_definitions: Iterable[ToolAction],
        raw_action_bindings: Iterable[Any],
    ) -> dict[int, list[object]]:
        action_definitions_by_id = {action.id: action for action in raw_action_definitions}

        action_lists: dict[int, list[object]] = defaultdict(list)
        for binding in raw_action_bindings:
            action_definition = action_definitions_by_id.get(binding.action_id)
            if action_definition is None:
                continue
            action_lists[binding.tool_id].append(
                SimpleNamespace(
                    id=binding.id,
                    action_id=action_definition.id,
                    slug=action_definition.slug,
                    name=action_definition.name,
                    description=action_definition.description,
                    constructor_params=binding.constructor_params or {},
                    response_title=binding.response_title,
                    priority=binding.priority,
                    is_active=binding.is_enabled,
                    metadata_json=binding.metadata_json,
                )
            )

        legacy_actions_by_tool_id: dict[int, list[ToolAction]] = defaultdict(list)
        for action in raw_action_definitions:
            tool_id = getattr(action, "tool_id", None)
            if tool_id is not None:
                legacy_actions_by_tool_id[tool_id].append(action)

        actions_by_tool_id: dict[int, list[object]] = {}
        for tool in tools:
            legacy_actions = legacy_actions_by_tool_id.get(tool.id, [])
            combined_actions = action_lists.get(tool.id, [])
            if legacy_actions:
                combined_actions = [*combined_actions, *legacy_actions]
            actions_by_tool_id[tool.id] = sorted(combined_actions, key=lambda item: item.priority)
        return actions_by_tool_id

    @classmethod
    def _group_bindings(
        cls,
        bindings: Iterable[Any],
        active_node_ids: set[int],
    ) -> dict[int, list[Any]]:
        """Group bindings by `node_id` and sort each list by `priority` desc.

        Generic over the three binding types (tool/mcp/skill); they all
        expose `node_id` and `priority` attributes.
        """
        grouped: dict[int, list[Any]] = defaultdict(list)
        for binding in bindings:
            if binding.node_id not in active_node_ids:
                continue
            grouped[binding.node_id].append(binding)
        return {
            node_id: sorted(items, key=lambda item: item.priority, reverse=True)
            for node_id, items in grouped.items()
        }

    @classmethod
    def _filter_edges(
        cls,
        edges: Iterable[AgentNodeEdge],
        active_node_ids: set[int],
    ) -> dict[int, list[AgentNodeEdge]]:
        edges_by_parent_id: dict[int, list[AgentNodeEdge]] = defaultdict(list)
        dangling_edges: list[int] = []
        for edge in edges:
            if edge.parent_node_id not in active_node_ids or edge.child_node_id not in active_node_ids:
                dangling_edges.append(edge.id)
                continue
            edges_by_parent_id[edge.parent_node_id].append(edge)
        sorted_edges = {
            parent_id: sorted(items, key=lambda item: item.priority, reverse=True)
            for parent_id, items in edges_by_parent_id.items()
        }
        if dangling_edges:
            logger.warning(
                "Skipping %s dangling edge(s) in cache: %s",
                len(dangling_edges),
                dangling_edges,
            )
        return sorted_edges

    @classmethod
    async def _build_cache(cls):
        raw = await cls._fetch_raw_data()
        nodes = raw["nodes"]
        edges = raw["edges"]
        tools = raw["tools"]
        mcp_servers = raw["mcp_servers"]
        skills = raw["skills"]

        active_node_ids = {node.id for node in nodes}

        actions_by_tool_id = cls._index_actions(
            tools=tools,
            raw_action_definitions=raw["action_definitions"],
            raw_action_bindings=raw["action_bindings"],
        )
        edges_by_parent_id = cls._filter_edges(edges, active_node_ids)
        tool_bindings_by_node_id = cls._group_bindings(raw["tool_bindings"], active_node_ids)
        mcp_bindings_by_node_id = cls._group_bindings(raw["mcp_bindings"], active_node_ids)
        skill_bindings_by_node_id = cls._group_bindings(raw["skill_bindings"], active_node_ids)

        nodes_by_id = {node.id: node for node in nodes}
        nodes_by_slug = {node.slug: node for node in nodes}
        tools_by_id = {tool.id: tool for tool in tools}
        tools_by_name = {tool.name: tool for tool in tools if tool.name}
        mcp_servers_by_id = {server.id: server for server in mcp_servers}
        skills_by_id = {skill.id: skill for skill in skills}

        # Build immutable snapshot first (tuples for binding lists).
        snapshot = GraphSnapshot(
            nodes_by_id=nodes_by_id,
            nodes_by_slug=nodes_by_slug,
            edges_by_parent_id={k: tuple(v) for k, v in edges_by_parent_id.items()},
            tool_bindings_by_node_id={k: tuple(v) for k, v in tool_bindings_by_node_id.items()},
            mcp_bindings_by_node_id={k: tuple(v) for k, v in mcp_bindings_by_node_id.items()},
            skill_bindings_by_node_id={k: tuple(v) for k, v in skill_bindings_by_node_id.items()},
            tools_by_id=tools_by_id,
            tools_by_name=tools_by_name,
            actions_by_tool_id={k: tuple(v) for k, v in actions_by_tool_id.items()},
            mcp_servers_by_id=mcp_servers_by_id,
            skills_by_id=skills_by_id,
        )

        # Atomic publish: snapshot first, then the legacy class-level views
        # are re-bound in one contiguous block. Reader on a single Python
        # statement boundary will see a self-consistent set.
        cls._snapshot = snapshot
        cls.nodes_by_id = nodes_by_id
        cls.nodes_by_slug = nodes_by_slug
        cls.edges_by_parent_id = edges_by_parent_id
        cls.tool_bindings_by_node_id = tool_bindings_by_node_id
        cls.mcp_bindings_by_node_id = mcp_bindings_by_node_id
        cls.skill_bindings_by_node_id = skill_bindings_by_node_id
        cls.tools_by_id = tools_by_id
        cls.tools_by_name = tools_by_name
        cls.actions_by_tool_id = actions_by_tool_id
        cls.mcp_servers_by_id = mcp_servers_by_id
        cls.skills_by_id = skills_by_id

        logger.info(
            "Platform cache built: nodes=%s edges=%s tools=%s mcp_servers=%s skills=%s",
            len(nodes),
            len(edges),
            len(tools),
            len(mcp_servers),
            len(skills),
        )

    @classmethod
    def get_node_by_id(cls, node_id: int) -> Optional[AgentNode]:
        return cls.nodes_by_id.get(node_id)

    @classmethod
    def get_node_by_slug(cls, slug: str) -> Optional[AgentNode]:
        return cls.nodes_by_slug.get(slug)

    @classmethod
    def get_children_edges(cls, node_id: int) -> list[AgentNodeEdge]:
        return list(cls.edges_by_parent_id.get(node_id, []))

    @classmethod
    def get_tool_bindings(cls, node_id: int) -> list[AgentNodeToolBinding]:
        return list(cls.tool_bindings_by_node_id.get(node_id, []))

    @classmethod
    def get_mcp_bindings(cls, node_id: int) -> list[AgentNodeMcpBinding]:
        return list(cls.mcp_bindings_by_node_id.get(node_id, []))

    @classmethod
    def get_skill_bindings(cls, node_id: int) -> list[AgentNodeSkillBinding]:
        return list(cls.skill_bindings_by_node_id.get(node_id, []))
