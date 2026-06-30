from typing import List, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.agent_node_skill_binding import AgentNodeSkillBinding
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.agent_node_skill_binding_schema import AgentNodeSkillBindingSchema
from setup.config import config


class AgentNodeSkillBindingRepo(MainRepositoryAbstract[AgentNodeSkillBinding, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "agent_node_skill_bindings"

    @classmethod
    def model(cls) -> Type[T]:
        return AgentNodeSkillBinding

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return AgentNodeSkillBindingSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_bindings(cls) -> List[AgentNodeSkillBinding]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSkillBindingSchema.IS_ENABLED).eq(True))
            .orderby(AgentNodeSkillBindingSchema.PRIORITY)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_node_id(cls, node_id: int) -> List[AgentNodeSkillBinding]:
        query = (
            cls.select_query()
            .where(cls.field(AgentNodeSkillBindingSchema.NODE_ID).eq(node_id))
            .where(cls.field(AgentNodeSkillBindingSchema.IS_ENABLED).eq(True))
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []
