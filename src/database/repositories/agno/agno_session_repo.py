from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T
from pypika import Order

from database.models.agno.agno_session import AgnoSession
from database.repositories.agno_repository_abstract import AgnoRepositoryAbstract
from database.schemas.agno.agno_session_schema import AgnoSessionSchema
from setup.config import config


class AgnoSessionRepo(AgnoRepositoryAbstract[AgnoSession, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return str(config.AGNO_DB_SCHEMA or "agno")

    @classmethod
    def table_name(cls) -> str:
        return str(config.AGNO_SESSION_TABLE or "agno_sessions")

    @classmethod
    def model(cls) -> Type[T]:
        return AgnoSession

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgnoSessionSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return False

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def find_by_id(
        cls,
        session_id: str,
        *,
        user_id: Optional[str] = None,
    ) -> Optional[AgnoSession]:
        query = (
            cls.select_query()
            .where(cls.field(AgnoSessionSchema.SESSION_ID).eq(session_id))
            .select("*")
        )
        if user_id:
            query = query.where(cls.field(AgnoSessionSchema.USER_ID).eq(user_id))
        return await cls.first(query)

    @classmethod
    async def list_recent(
        cls,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        team_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        session_type: Optional[str] = None,
        limit: int = 20,
        page: int = 1,
    ) -> tuple[List[AgnoSession], int]:
        base = cls.select_query()
        if user_id:
            base = base.where(cls.field(AgnoSessionSchema.USER_ID).eq(user_id))
        if agent_id:
            base = base.where(cls.field(AgnoSessionSchema.AGENT_ID).eq(agent_id))
        if team_id:
            base = base.where(cls.field(AgnoSessionSchema.TEAM_ID).eq(team_id))
        if workflow_id:
            base = base.where(cls.field(AgnoSessionSchema.WORKFLOW_ID).eq(workflow_id))
        if session_type:
            base = base.where(cls.field(AgnoSessionSchema.SESSION_TYPE).eq(session_type))

        total = await cls.count(base)
        offset = max(0, (page - 1) * limit)
        items_query = (
            base.select("*")
            .orderby(AgnoSessionSchema.UPDATED_AT, order=Order.desc)
            .limit(limit)
            .offset(offset)
        )
        items = await cls.get(items_query)
        return items or [], total
