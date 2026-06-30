from typing import Any

from api.errors import ConflictError, NotFoundError
from database.repositories.main.agent_node_edge_repo import AgentNodeEdgeRepo
from database.repositories.main.agent_channel_repo import AgentChannelRepo
from database.repositories.main.agent_node_mcp_binding_repo import AgentNodeMcpBindingRepo
from database.repositories.main.agent_node_skill_binding_repo import AgentNodeSkillBindingRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from database.repositories.main.agent_node_tool_binding_repo import AgentNodeToolBindingRepo
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.translator import trans

from services.platform.admin._shared import normalize_payload


class NodeAdminService:
    @staticmethod
    async def list_nodes() -> list[Any]:
        return await AgentNodeRepo.get_all_active_nodes()

    @staticmethod
    async def create_node(payload: dict) -> Any:
        existing = await AgentNodeRepo.find_active_by_slug(payload["slug"])
        if existing:
            raise ConflictError(trans("errors.platform.admin.node_slug_exists", slug=payload["slug"]))
        prepared_payload = normalize_payload("node", payload)
        result = await AgentNodeRepo.create_return(prepared_payload)
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def update_node(node_id: int, payload: dict) -> Any:
        current_node = await AgentNodeRepo.find_active_by_id(node_id)
        if current_node is None:
            raise NotFoundError(trans("errors.platform.admin.node_not_found", node_id=node_id))
        if "slug" in payload:
            existing = await AgentNodeRepo.find_active_by_slug(payload["slug"])
            if existing and existing.id != node_id:
                raise ConflictError(trans("errors.platform.admin.node_slug_exists", slug=payload["slug"]))
        prepared_payload = normalize_payload("node", payload)
        if prepared_payload:
            result = await AgentNodeRepo.update_by_id(node_id, prepared_payload, return_=True)
        else:
            result = current_node
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def deactivate_node(node_id: int) -> Any:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        if node is None:
            raise NotFoundError(trans("errors.platform.admin.node_not_found", node_id=node_id))

        edges_as_parent = await AgentNodeEdgeRepo.find_active_by_parent_id(node_id)
        edges_as_child = await AgentNodeEdgeRepo.find_active_by_child_id(node_id)
        edge_ids = {edge.id for edge in (*edges_as_parent, *edges_as_child)}
        for edge_id in edge_ids:
            await AgentNodeEdgeRepo.update_by_id(edge_id, {"is_active": False})

        for binding in await AgentNodeToolBindingRepo.find_active_by_node_id(node_id):
            await AgentNodeToolBindingRepo.update_by_id(binding.id, {"is_active": False})

        for binding in await AgentNodeMcpBindingRepo.find_active_by_node_id(node_id):
            await AgentNodeMcpBindingRepo.update_by_id(binding.id, {"is_active": False})

        for binding in await AgentNodeSkillBindingRepo.find_active_by_node_id(node_id):
            await AgentNodeSkillBindingRepo.update_by_id(binding.id, {"is_active": False})

        for channel in await AgentChannelRepo.list_by_node_id(node_id):
            if channel.is_enabled:
                await AgentChannelRepo.update_by_id(
                    channel.id, {"is_enabled": False}
                )

        result = await AgentNodeRepo.update_by_id(node_id, {"is_active": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result
