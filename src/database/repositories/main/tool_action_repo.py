import logging
from typing import List, Optional, Type
from database.models.main.tool_action import ToolAction
from database.schemas.main.tool_action_schema import ToolActionSchema
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from basalam.backbone_orm import T, ModelSchemaAbstract, QueryBuilderAbstract
from setup.config import config

logger = logging.getLogger(__name__)


class ToolActionRepo(MainRepositoryAbstract[ToolAction, QueryBuilderAbstract]):

    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return 'tool_actions'

    @classmethod
    def model(cls) -> Type[T]:
        return ToolAction

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return ToolActionSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_actions_by_tool_id(cls, tool_id: int) -> List[ToolAction]:
        query = (
            cls.select_query()
            .where(cls.field(ToolActionSchema.TOOL_ID).eq(tool_id))
            .where(cls.field(ToolActionSchema.IS_ACTIVE).eq(True))
            .orderby(ToolActionSchema.PRIORITY)
            .select("*")
        )

        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_all_active_actions(cls) -> List[ToolAction]:
        query = (
            cls.select_query()
            .where(cls.field(ToolActionSchema.IS_ACTIVE).eq(True))
            .orderby(ToolActionSchema.PRIORITY)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_id(cls, action_id: int) -> Optional[ToolAction]:
        query = (
            cls.select_query()
            .where(cls.field(ToolActionSchema.ID).eq(action_id))
            .where(cls.field(ToolActionSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_active_by_slug(cls, slug: str) -> Optional[ToolAction]:
        query = (
            cls.select_query()
            .where(cls.field(ToolActionSchema.SLUG).eq(slug))
            .where(cls.field(ToolActionSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)
