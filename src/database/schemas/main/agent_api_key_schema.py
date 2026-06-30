from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgentApiKeySchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    NODE_ID: ClassVar[str] = "node_id"
    NAME: ClassVar[str] = "name"
    KEY_PREFIX: ClassVar[str] = "key_prefix"
    KEY_HASH: ClassVar[str] = "key_hash"
    EXPIRES_AT: ClassVar[str] = "expires_at"
    IS_ACTIVE: ClassVar[str] = "is_active"
    LAST_USED_AT: ClassVar[str] = "last_used_at"
    REVOKED_AT: ClassVar[str] = "revoked_at"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
