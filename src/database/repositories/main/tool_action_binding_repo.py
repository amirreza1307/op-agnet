from typing import List, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.tool_action_binding import ToolActionBinding
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.tool_action_binding_schema import ToolActionBindingSchema
from setup.config import config


class ToolActionBindingRepo(MainRepositoryAbstract[ToolActionBinding, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "tool_action_bindings"

    @classmethod
    def model(cls) -> Type[T]:
        return ToolActionBinding

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return ToolActionBindingSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_bindings(cls) -> List[ToolActionBinding]:
        query = (
            cls.select_query()
            .where(cls.field(ToolActionBindingSchema.IS_ENABLED).eq(True))
            .orderby(ToolActionBindingSchema.PRIORITY)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_bindings_by_tool_id(cls, tool_id: int) -> List[ToolActionBinding]:
        query = (
            cls.select_query()
            .where(cls.field(ToolActionBindingSchema.TOOL_ID).eq(tool_id))
            .where(cls.field(ToolActionBindingSchema.IS_ENABLED).eq(True))
            .orderby(ToolActionBindingSchema.PRIORITY)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []
