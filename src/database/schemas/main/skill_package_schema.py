from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class SkillPackageSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    SLUG: ClassVar[str] = "slug"
    NAME: ClassVar[str] = "name"
    DESCRIPTION: ClassVar[str] = "description"
    SOURCE_PATH: ClassVar[str] = "source_path"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    IS_ACTIVE: ClassVar[str] = "is_active"
    IS_PUBLIC: ClassVar[str] = "is_public"
    PUBLIC_NAME: ClassVar[str] = "public_name"
    CREATED_BY: ClassVar[str] = "created_by"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
