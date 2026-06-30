from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from database.models.main.agent_node import AgentNode
from database.models.main.agent_node_edge import AgentNodeEdge
from database.models.main.agent_node_mcp_binding import AgentNodeMcpBinding
from database.models.main.agent_node_skill_binding import AgentNodeSkillBinding
from database.models.main.agent_node_tool_binding import AgentNodeToolBinding
from database.models.main.mcp_server import McpServer
from database.models.main.skill_package import SkillPackage
from database.models.main.tool import Tool


@dataclass(frozen=True)
class GraphSnapshot:
    """Immutable, atomic view of the platform graph.

    All collections are read-only Mappings of (node_id|slug|tool_id) -> entity
    or tuples of entities. Replacing the snapshot is a single atomic
    assignment so concurrent readers never observe a half-built state.
    """

    nodes_by_id: Mapping[int, AgentNode] = field(default_factory=dict)
    nodes_by_slug: Mapping[str, AgentNode] = field(default_factory=dict)
    edges_by_parent_id: Mapping[int, tuple[AgentNodeEdge, ...]] = field(default_factory=dict)
    tool_bindings_by_node_id: Mapping[int, tuple[AgentNodeToolBinding, ...]] = field(default_factory=dict)
    mcp_bindings_by_node_id: Mapping[int, tuple[AgentNodeMcpBinding, ...]] = field(default_factory=dict)
    skill_bindings_by_node_id: Mapping[int, tuple[AgentNodeSkillBinding, ...]] = field(default_factory=dict)
    tools_by_id: Mapping[int, Tool] = field(default_factory=dict)
    tools_by_name: Mapping[str, Tool] = field(default_factory=dict)
    actions_by_tool_id: Mapping[int, tuple[Any, ...]] = field(default_factory=dict)
    mcp_servers_by_id: Mapping[int, McpServer] = field(default_factory=dict)
    skills_by_id: Mapping[int, SkillPackage] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "GraphSnapshot":
        return cls()
