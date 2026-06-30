import logging
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from api.errors import BadRequestError, ConflictError, NotFoundError
from database.models.main.agent_node import AgentNode
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.translator import trans

logger = logging.getLogger(__name__)


class NodeGraphView(BaseModel):
    """Typed DTO for the recursive graph view returned by `get_graph`.

    Replaces the previous untyped dict. Wire format is preserved by
    serialising via `model_dump(mode="json")` so existing consumers
    (admin query layer, runtime node builder) continue to receive a
    plain dict shape.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_base_url: Optional[str] = None
    session_table: Optional[str] = None
    runtime_config_json: Optional[Any] = None
    children: list["NodeGraphView"] = Field(default_factory=list)


NodeGraphView.model_rebuild()


class NodeRegistryService:
    @staticmethod
    async def resolve(node_id: Optional[int] = None, slug: Optional[str] = None) -> AgentNode:
        await PlatformCacheManager.load()
        if node_id is not None:
            node = PlatformCacheManager.get_node_by_id(node_id)
        elif slug is not None:
            node = PlatformCacheManager.get_node_by_slug(slug)
        else:
            raise BadRequestError(trans("errors.platform.graph.node_id_or_slug_required"))

        if node is None:
            raise NotFoundError(trans("errors.platform.graph.node_not_found"))
        return node

    @staticmethod
    async def get_graph(node: AgentNode) -> dict:
        await PlatformCacheManager.load()

        def build(node_id: int, active_path: set[int]) -> Optional[NodeGraphView]:
            if node_id in active_path:
                raise ConflictError(trans("errors.platform.graph.cycle_at_node", node_id=node_id))
            current = PlatformCacheManager.get_node_by_id(node_id)
            if current is None:
                logger.warning("Skipping missing node %s while building graph", node_id)
                return None
            next_path = set(active_path)
            next_path.add(node_id)
            children: list[NodeGraphView] = []
            for edge in PlatformCacheManager.get_children_edges(node_id):
                child = build(edge.child_node_id, next_path)
                if child is not None:
                    children.append(child)
            return NodeGraphView(
                id=current.id,
                slug=current.slug,
                name=current.name,
                description=current.description,
                system_prompt=current.system_prompt,
                model_id=current.model_id,
                model_provider=current.model_provider,
                model_base_url=current.model_base_url,
                session_table=current.session_table,
                runtime_config_json=current.runtime_config_json,
                children=children,
            )

        result = build(node.id, set())
        if result is None:
            raise NotFoundError(trans("errors.platform.graph.node_id_not_in_cache", node_id=node.id))
        return result.model_dump(mode="json")
