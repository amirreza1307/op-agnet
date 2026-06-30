from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class ToolActionBindingSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    TOOL_ID: ClassVar[str] = "tool_id"
    ACTION_ID: ClassVar[str] = "action_id"
    CONSTRUCTOR_PARAMS: ClassVar[str] = "constructor_params"
    RESPONSE_TITLE: ClassVar[str] = "response_title"
    PRIORITY: ClassVar[str] = "priority"
    IS_ENABLED: ClassVar[str] = "is_enabled"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
