from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.message_feedback import MessageFeedback
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.message_feedback_schema import MessageFeedbackSchema
from setup.config import config


class MessageFeedbackRepo(MainRepositoryAbstract[MessageFeedback, QueryBuilderAbstract]):

    @classmethod
    def schema_name(cls) -> str:
        return config.VENDOR_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return 'message_feedbacks'

    @classmethod
    def model(cls) -> Type[T]:
        return MessageFeedback

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return MessageFeedbackSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return False

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def find_existing(
        cls,
        *,
        vendor_id: int,
        session_id: str,
        message_id: str,
    ) -> Optional[MessageFeedback]:
        """Return the row that matches the upsert scope, if any.

        Scope: ``(vendor_id, session_id, message_id)``. A unique index
        guarantees at most one row per scope.
        """
        query = (
            cls.select_query()
            .where(cls.field(MessageFeedbackSchema.VENDOR_ID).eq(vendor_id))
            .where(cls.field(MessageFeedbackSchema.SESSION_ID).eq(session_id))
            .where(cls.field(MessageFeedbackSchema.MESSAGE_ID).eq(message_id))
            .select("*")
        )
        rows = await cls.get(query)
        return rows[0] if rows else None

    @classmethod
    async def list_for_session(
        cls,
        *,
        vendor_id: int,
        session_id: str,
    ) -> List[MessageFeedback]:
        query = (
            cls.select_query()
            .where(cls.field(MessageFeedbackSchema.VENDOR_ID).eq(vendor_id))
            .where(cls.field(MessageFeedbackSchema.SESSION_ID).eq(session_id))
            .select("*")
        )
        return await cls.get(query)
