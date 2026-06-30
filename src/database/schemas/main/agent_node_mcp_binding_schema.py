from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgentNodeMcpBindingSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    NODE_ID: ClassVar[str] = "node_id"
    MCP_SERVER_ID: ClassVar[str] = "mcp_server_id"
    PRIORITY: ClassVar[str] = "priority"
    IS_ENABLED: ClassVar[str] = "is_enabled"
    BINDING_MODE: ClassVar[str] = "binding_mode"
    HEADER_TEMPLATE_JSON: ClassVar[str] = "header_template_json"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
