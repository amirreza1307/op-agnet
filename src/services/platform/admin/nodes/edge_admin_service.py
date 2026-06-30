from typing import Any

from api.errors import NotFoundError
from database.repositories.main.agent_node_edge_repo import AgentNodeEdgeRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from services.platform.graph.graph_validation_service import GraphValidationService
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.translator import trans

from services.platform.admin._shared import normalize_payload


class EdgeAdminService:
    @staticmethod
    async def create_edge(payload: dict) -> Any:
        parent = await AgentNodeRepo.find_active_by_id(payload["parent_node_id"])
        child = await AgentNodeRepo.find_active_by_id(payload["child_node_id"])
        if parent is None or child is None:
            raise NotFoundError(trans("errors.platform.admin.parent_and_child_node_required"))
        # Validate against the current snapshot before mutating the DB —
        # a single refresh after the write is enough to publish the new edge.
        await PlatformCacheManager.load()
        GraphValidationService.validate_no_cycle_from(payload["parent_node_id"], payload["child_node_id"])
        result = await AgentNodeEdgeRepo.create_return(normalize_payload("edge", payload))
        await PlatformCacheManager.refresh()
        return result

    @staticmethod
    async def deactivate_edge(edge_id: int) -> Any:
        edges = await AgentNodeEdgeRepo.get_all_active_edges()
        edge = next((item for item in edges if item.id == edge_id), None)
        if edge is None:
            raise NotFoundError(trans("errors.platform.admin.edge_not_found", edge_id=edge_id))
        result = await AgentNodeEdgeRepo.update_by_id(edge_id, {"is_active": False}, return_=True)
        await PlatformCacheManager.refresh()
        return result
