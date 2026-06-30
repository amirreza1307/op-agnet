from typing import List, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.llm_request_log import LlmRequestLog
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.llm_request_log_schema import LlmRequestLogSchema
from setup.config import config


class LlmRequestLogRepo(MainRepositoryAbstract[LlmRequestLog, QueryBuilderAbstract]):

    @classmethod
    def schema_name(cls) -> str:
        return config.VENDOR_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return 'llm_request_logs'

    @classmethod
    def model(cls) -> Type[T]:
        return LlmRequestLog

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return LlmRequestLogSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return False

    @classmethod
    def default_relations(cls) -> List[str]:
        return []
