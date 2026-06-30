from typing import List, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.agent_node_edge import AgentNodeEdge
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.agent_node_edge_schema import AgentNodeEdgeSchema
from setup.config import config


class AgentNodeEdgeRepo(MainRepositoryAbstract[AgentNodeEdge, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "agent_node_edges"

    @classmethod
    def model(cls) -> Type[T]:
        return AgentNodeEdge

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgentNodeEdgeSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_edges(cls) -> List[AgentNodeEdge]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeEdgeSchema.IS_ACTIVE).eq(True))
            .orderby(AgentNodeEdgeSchema.PRIORITY)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_parent_id(cls, parent_node_id: int) -> List[AgentNodeEdge]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeEdgeSchema.PARENT_NODE_ID).eq(parent_node_id))
            .where(cls.field(AgentNodeEdgeSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_child_id(cls, child_node_id: int) -> List[AgentNodeEdge]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeEdgeSchema.CHILD_NODE_ID).eq(child_node_id))
            .where(cls.field(AgentNodeEdgeSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []
