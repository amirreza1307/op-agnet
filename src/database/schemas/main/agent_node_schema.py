from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgentNodeSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    SLUG: ClassVar[str] = "slug"
    NAME: ClassVar[str] = "name"
    DESCRIPTION: ClassVar[str] = "description"
    SYSTEM_PROMPT: ClassVar[str] = "system_prompt"
    MODEL_ID: ClassVar[str] = "model_id"
    MODEL_PROVIDER: ClassVar[str] = "model_provider"
    MODEL_API_KEY: ClassVar[str] = "model_api_key"
    MODEL_BASE_URL: ClassVar[str] = "model_base_url"
    SESSION_TABLE: ClassVar[str] = "session_table"
    RUNTIME_CONFIG_JSON: ClassVar[str] = "runtime_config_json"
    IS_ACTIVE: ClassVar[str] = "is_active"
    IS_PUBLIC: ClassVar[str] = "is_public"
    PUBLIC_NAME: ClassVar[str] = "public_name"
    IMAGE_FILE_ID: ClassVar[str] = "image_file_id"
    PRIORITY: ClassVar[str] = "priority"
    VERSION: ClassVar[str] = "version"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    CREATED_BY: ClassVar[str] = "created_by"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
