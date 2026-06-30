from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class ToolKnowledgeNodeSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    TOOL_SLUG: ClassVar[str] = "tool_slug"
    TITLE: ClassVar[str] = "title"
    CONTENT: ClassVar[str] = "content"
    PRIORITY: ClassVar[str] = "priority"
    IS_ACTIVE: ClassVar[str] = "is_active"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
