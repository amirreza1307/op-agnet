from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.agent_channel_update import AgentChannelUpdate
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.agent_channel_update_schema import AgentChannelUpdateSchema
from setup.config import config


class AgentChannelUpdateRepo(
    MainRepositoryAbstract[AgentChannelUpdate, QueryBuilderAbstract]
):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "agent_channel_updates"

    @classmethod
    def model(cls) -> Type[T]:
        return AgentChannelUpdate

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgentChannelUpdateSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return False

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def find_by_provider_id(
        cls, channel_id: int, provider_update_id: int
    ) -> Optional[AgentChannelUpdate]:
        query = (
            cls.select_query()
            .where(cls.field(AgentChannelUpdateSchema.CHANNEL_ID).eq(channel_id))
            .where(
                cls.field(AgentChannelUpdateSchema.PROVIDER_UPDATE_ID).eq(
                    provider_update_id
                )
            )
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def claim(
        cls, channel_id: int, provider_update_id: int
    ) -> Optional[AgentChannelUpdate]:
        connection = await cls.connection()
        rows = await connection.execute_and_fetch(
            f"""
            INSERT INTO {config.PLATFORM_SCHEMA}.agent_channel_updates
                (channel_id, provider_update_id, status)
            VALUES ($1, $2, 'processing')
            ON CONFLICT (channel_id, provider_update_id) DO NOTHING
            RETURNING *
            """,
            [channel_id, provider_update_id],
        )
        if not rows:
            return None
        return AgentChannelUpdate(**rows[0])
