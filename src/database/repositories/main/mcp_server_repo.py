from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.mcp_server import McpServer
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.mcp_server_schema import McpServerSchema
from setup.config import config


class McpServerRepo(MainRepositoryAbstract[McpServer, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "mcp_servers"

    @classmethod
    def model(cls) -> Type[T]:
        return McpServer

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return McpServerSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_servers(cls) -> List[McpServer]:
        query = (
            cls.select_query()
            .where(cls.field(McpServerSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_id(cls, server_id: int) -> Optional[McpServer]:
        query = (
            cls.select_query()
            .where(cls.field(McpServerSchema.ID).eq(server_id))
            .where(cls.field(McpServerSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_active_by_slug(cls, slug: str) -> Optional[McpServer]:
        query = (
            cls.select_query()
            .where(cls.field(McpServerSchema.SLUG).eq(slug))
            .where(cls.field(McpServerSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def get_public_servers(cls) -> List[McpServer]:
        query = (
            cls.select_query()
            .where(cls.field(McpServerSchema.IS_ACTIVE).eq(True))
            .where(cls.field(McpServerSchema.IS_PUBLIC).eq(True))
            .orderby(McpServerSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_servers_by_creator(cls, user_id: int) -> List[McpServer]:
        query = (
            cls.select_query()
            .where(cls.field(McpServerSchema.IS_ACTIVE).eq(True))
            .where(cls.field(McpServerSchema.CREATED_BY).eq(user_id))
            .orderby(McpServerSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_visible_servers(cls, user_id: int) -> List[McpServer]:
        own = await cls.get_servers_by_creator(user_id)
        public = await cls.get_public_servers()
        seen = {server.id for server in own}
        merged = list(own)
        for server in public:
            if server.id not in seen:
                merged.append(server)
        return merged
