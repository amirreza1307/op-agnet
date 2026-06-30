from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgentNodeEdgeSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    PARENT_NODE_ID: ClassVar[str] = "parent_node_id"
    CHILD_NODE_ID: ClassVar[str] = "child_node_id"
    PRIORITY: ClassVar[str] = "priority"
    IS_ACTIVE: ClassVar[str] = "is_active"
    MEMBER_INSTRUCTIONS_JSON: ClassVar[str] = "member_instructions_json"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
