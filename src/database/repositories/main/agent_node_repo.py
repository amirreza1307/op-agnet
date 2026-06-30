from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.agent_node import AgentNode
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.agent_node_schema import AgentNodeSchema
from setup.config import config


class AgentNodeRepo(MainRepositoryAbstract[AgentNode, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "agent_nodes"

    @classmethod
    def model(cls) -> Type[T]:
        return AgentNode

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgentNodeSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_nodes(cls) -> List[AgentNode]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSchema.IS_ACTIVE).eq(True))
            .orderby(AgentNodeSchema.PRIORITY)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_id(cls, node_id: int) -> Optional[AgentNode]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSchema.ID).eq(node_id))
            .where(cls.field(AgentNodeSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_active_by_slug(cls, slug: str) -> Optional[AgentNode]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSchema.SLUG).eq(slug))
            .where(cls.field(AgentNodeSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def get_public_nodes(cls) -> List[AgentNode]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSchema.IS_ACTIVE).eq(True))
            .where(cls.field(AgentNodeSchema.IS_PUBLIC).eq(True))
            .orderby(AgentNodeSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_nodes_by_creator(cls, user_id: int) -> List[AgentNode]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSchema.IS_ACTIVE).eq(True))
            .where(cls.field(AgentNodeSchema.CREATED_BY).eq(user_id))
            .orderby(AgentNodeSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_visible_nodes(cls, user_id: int) -> List[AgentNode]:
        own = await cls.get_nodes_by_creator(user_id)
        public = await cls.get_public_nodes()
        seen = {node.id for node in own}
        merged = list(own)
        for node in public:
            if node.id not in seen:
                merged.append(node)
        return merged
