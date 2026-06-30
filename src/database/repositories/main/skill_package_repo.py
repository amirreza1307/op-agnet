from typing import List, Optional, Type

from basalam.backbone_orm import ModelSchemaAbstract, QueryBuilderAbstract, T

from database.models.main.skill_package import SkillPackage
from database.repositories.main_repository_abstract import MainRepositoryAbstract
from database.schemas.main.skill_package_schema import SkillPackageSchema
from setup.config import config


class SkillPackageRepo(MainRepositoryAbstract[SkillPackage, QueryBuilderAbstract]):
    @classmethod
    def schema_name(cls) -> str:
        return config.PLATFORM_SCHEMA

    @classmethod
    def table_name(cls) -> str:
        return "skill_packages"

    @classmethod
    def model(cls) -> Type[T]:
        return SkillPackage

    @classmethod
    def schema(cls) -> Type[ModelSchemaAbstract]:
        return SkillPackageSchema

    @classmethod
    def soft_deletes(cls) -> bool:
        return True

    @classmethod
    def default_relations(cls) -> List[str]:
        return []

    @classmethod
    async def get_all_active_skills(cls) -> List[SkillPackage]:
        query = cls.select_query().where(cls.field(SkillPackageSchema.IS_ACTIVE).eq(True)).select("*")
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def find_active_by_id(cls, skill_id: int) -> Optional[SkillPackage]:
        query = (
            cls.select_query()
            .where(cls.field(SkillPackageSchema.ID).eq(skill_id))
            .where(cls.field(SkillPackageSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def find_active_by_slug(cls, slug: str) -> Optional[SkillPackage]:
        query = (
            cls.select_query()
            .where(cls.field(SkillPackageSchema.SLUG).eq(slug))
            .where(cls.field(SkillPackageSchema.IS_ACTIVE).eq(True))
            .select("*")
        )
        return await cls.first(query)

    @classmethod
    async def get_public_skills(cls) -> List[SkillPackage]:
        query = (
            cls.select_query()
            .where(cls.field(SkillPackageSchema.IS_ACTIVE).eq(True))
            .where(cls.field(SkillPackageSchema.IS_PUBLIC).eq(True))
            .orderby(SkillPackageSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_skills_by_creator(cls, user_id: int) -> List[SkillPackage]:
        query = (
            cls.select_query()
            .where(cls.field(SkillPackageSchema.IS_ACTIVE).eq(True))
            .where(cls.field(SkillPackageSchema.CREATED_BY).eq(user_id))
            .orderby(SkillPackageSchema.NAME)
            .select("*")
        )
        results = await cls.get(query)
        return results if results else []

    @classmethod
    async def get_visible_skills(cls, user_id: int) -> List[SkillPackage]:
        own = await cls.get_skills_by_creator(user_id)
        public = await cls.get_public_skills()
        seen = {skill.id for skill in own}
        merged = list(own)
        for skill in public:
            if skill.id not in seen:
                merged.append(skill)
        return merged
