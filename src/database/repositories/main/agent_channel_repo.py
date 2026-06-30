from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.agent_channel import AgentChannel
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.agent_channel_schema import AgentChannelSchema
from setup.config import config


class AgentChannelRepo(MainRepositoryAbstract[AgentChannel, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "agent_channels"

    @classmethod
    def model(cls) -> Type[T]:
        return AgentChannel

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgentChannelSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def find_by_id(cls, channel_id: int) -> Optional[AgentChannel]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelSchema.ID).eq(channel_id))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_enabled_by_id(cls, channel_id: int) -> Optional[AgentChannel]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelSchema.ID).eq(channel_id))
            .where(cls.field(AgentChannelSchema.IS_ENABLED).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_by_node_and_type(
        cls, node_id: int, channel_type: str
    ) -> Optional[AgentChannel]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelSchema.NODE_ID).eq(node_id))
            .where(cls.field(AgentChannelSchema.CHANNEL_TYPE).eq(channel_type))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_by_token_hash(cls, token_hash: str) -> Optional[AgentChannel]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelSchema.TOKEN_HASH).eq(token_hash))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def list_by_node_id(cls, node_id: int) -> List[AgentChannel]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelSchema.NODE_ID).eq(node_id))
            .orderby(AgentChannelSchema.CHANNEL_TYPE)
            .select("*")
        )
        return await cls.get(query) or []

    @classmethod
    async def get_all_enabled(cls) -> List[AgentChannel]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelSchema.IS_ENABLED).eq(True))
            .select("*")
        )
        return await cls.get(query) or []
