from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T
from pypika import Order

from database.models.main.agent_api_key import AgentApiKey
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.agent_api_key_schema import AgentApiKeySchema
from setup.config import config


class AgentApiKeyRepo(MainRepositoryAbstract[AgentApiKey, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "agent_api_keys"

    @classmethod
    def model(cls) -> Type[T]:
        return AgentApiKey

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgentApiKeySchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return False

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def find_active_by_hash(cls, key_hash: str) -> Optional[AgentApiKey]:
        query = (
            cls.select_query()
            .where(cls.field(AgentApiKeySchema.KEY_HASH).eq(key_hash))
            .where(cls.field(AgentApiKeySchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_by_id_and_node(
        cls, key_id: int, node_id: int
    ) -> Optional[AgentApiKey]:
        query = (
            cls.select_query()
            .where(cls.field(AgentApiKeySchema.ID).eq(key_id))
            .where(cls.field(AgentApiKeySchema.NODE_ID).eq(node_id))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def list_by_node_id(cls, node_id: int) -> List[AgentApiKey]:
        query = (
            cls.select_query()
            .where(cls.field(AgentApiKeySchema.NODE_ID).eq(node_id))
            .orderby(AgentApiKeySchema.CREATED_AT, order=Order.desc)
            .select("*")
        )
        return await cls.get(query) or []
