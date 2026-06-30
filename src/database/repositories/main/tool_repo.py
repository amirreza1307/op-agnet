import logging
import sentry_sdk
from typing import List, Type, Optional
from database.models.main.tool import Tool
from database.schemas.main.tool_schema import ToolSchema
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from basalam.backbone_orm import T, ModelSchemaAbstract, QueryBuilderAbstract
from setup.config import config

logger = logging.getLogger(__name__)


class ToolRepo(MainRepositoryAbstract[Tool, QueryBuilderAbstract]):

    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return 'tools'

    @classmethod
    def model(cls) -> Type[T]:
        return Tool

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return ToolSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_tools(cls) -> List[Tool]:
        query = (
            cls.select_query()
            .where(cls.field(ToolSchema.IS_ACTIVE).eq(True))
            .orderby(ToolSchema.NAME)
            .select("*")
        )

        results = await cls.get(query)

        if not results:
            error_msg = "No active tools found in database"
            logger.warning(error_msg)
            return []

        logger.info(f"Loaded {len(results)} active tools from database")
        return results

    @classmethod
    async def find_active_by_id(cls, tool_id: int) -> Optional[Tool]:
        query = (
            cls.select_query()
            .where(cls.field(ToolSchema.ID).eq(tool_id))
            .where(cls.field(ToolSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_active_by_slug(cls, slug: str) -> Optional[Tool]:
        query = (
            cls.select_query()
            .where(cls.field(ToolSchema.SLUG).eq(slug))
            .where(cls.field(ToolSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def get_tools_by_agent_id(cls, agent_id: int) -> List[Tool]:
        query = (
            cls.select_query()
            .where(cls.field(ToolSchema.IS_ACTIVE).eq(True))
            .where(cls.field(ToolSchema.AGENT_ID).eq(agent_id))
            .select("*")
        )

        results = await cls.get(query)

        if not results:
            logger.info(f"No active tools found for agent_id={agent_id}")
            return []

        logger.info(f"Loaded {len(results)} active tools for agent_id={agent_id}")
        return results

    @classmethod
    async def get_public_tools(cls) -> List[Tool]:
        query = (
            cls.select_query()
            .where(cls.field(ToolSchema.IS_ACTIVE).eq(True))
            .where(cls.field(ToolSchema.IS_PUBLIC).eq(True))
            .orderby(ToolSchema.NAME)
            .select("*")
        )

        results = await cls.get(query)

        if not results:
            logger.info("No public tools found in database")
            return []

        logger.info(f"Loaded {len(results)} public tools from database")
        return results

    @classmethod
    async def get_tools_by_creator(cls, user_id: int) -> List[Tool]:
        query = (
            cls.select_query()
            .where(cls.field(ToolSchema.IS_ACTIVE).eq(True))
            .where(cls.field(ToolSchema.CREATED_BY).eq(user_id))
            .orderby(ToolSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_visible_tools(cls, user_id: int) -> List[Tool]:
        own = await cls.get_tools_by_creator(user_id)
        public = await cls.get_public_tools()
        seen = {tool.id for tool in own}
        merged = list(own)
        for tool in public:
            if tool.id not in seen:
                merged.append(tool)
        return merged
