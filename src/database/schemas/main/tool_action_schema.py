from typing import ClassVar
from basalam.backbone_orm import ModelSchemaAbstract


class ToolActionSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = 'id'
    TOOL_ID: ClassVar[str] = 'tool_id'
    SLUG: ClassVar[str] = 'slug'
    NAME: ClassVar[str] = 'name'
    DESCRIPTION: ClassVar[str] = 'description'
    FA_NAME: ClassVar[str] = 'fa_name'
    FA_DESCRIPTION: ClassVar[str] = 'fa_description'
    CONSTRUCTOR_PARAMS: ClassVar[str] = 'constructor_params'
    RESPONSE_TITLE: ClassVar[str] = 'response_title'
    PRIORITY: ClassVar[str] = 'priority'
    IS_ACTIVE: ClassVar[str] = 'is_active'
    METADATA_JSON: ClassVar[str] = 'metadata_json'
    CREATED_AT: ClassVar[str] = 'created_at'
    UPDATED_AT: ClassVar[str] = 'updated_at'
    DELETED_AT: ClassVar[str] = 'deleted_at'
