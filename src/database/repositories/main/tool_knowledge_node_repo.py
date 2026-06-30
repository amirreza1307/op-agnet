from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.tool_knowledge_node import ToolKnowledgeNode
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.tool_knowledge_node_schema import ToolKnowledgeNodeSchema
from setup.config import config


class ToolKnowledgeNodeRepo(
    MainRepositoryAbstract[ToolKnowledgeNode, QueryBuilderAbstract]
):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "tool_knowledge_nodes"

    @classmethod
    def model(cls) -> Type[T]:
        return ToolKnowledgeNode

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return ToolKnowledgeNodeSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_active_by_tool_slug(
        cls, tool_slug: str
    ) -> List[ToolKnowledgeNode]:
        query = (
            cls.select_query()
            .where(cls.field(ToolKnowledgeNodeSchema.TOOL_SLUG).eq(tool_slug))
            .where(cls.field(ToolKnowledgeNodeSchema.IS_ACTIVE).eq(True))
            .orderby(ToolKnowledgeNodeSchema.PRIORITY)
            .orderby(ToolKnowledgeNodeSchema.ID)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def list_nodes(
        cls,
        *,
        tool_slug: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[ToolKnowledgeNode]:
        query = cls.select_query()
        if tool_slug:
            query = query.where(
                cls.field(ToolKnowledgeNodeSchema.TOOL_SLUG).eq(tool_slug)
            )
        if not include_inactive:
            query = query.where(
                cls.field(ToolKnowledgeNodeSchema.IS_ACTIVE).eq(True)
            )
        query = (
            query.orderby(ToolKnowledgeNodeSchema.TOOL_SLUG)
            .orderby(ToolKnowledgeNodeSchema.PRIORITY)
            .orderby(ToolKnowledgeNodeSchema.ID)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_id(
        cls, knowledge_node_id: int
    ) -> Optional[ToolKnowledgeNode]:
        query = (
            cls.select_query()
            .where(cls.field(ToolKnowledgeNodeSchema.ID).eq(knowledge_node_id))
            .where(cls.field(ToolKnowledgeNodeSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)
