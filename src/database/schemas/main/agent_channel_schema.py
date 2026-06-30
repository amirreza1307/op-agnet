from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgentChannelSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    NODE_ID: ClassVar[str] = "node_id"
    CHANNEL_TYPE: ClassVar[str] = "channel_type"
    NAME: ClassVar[str] = "name"
    BOT_TOKEN_ENCRYPTED: ClassVar[str] = "bot_token_encrypted"
    TOKEN_HASH: ClassVar[str] = "token_hash"
    TOKEN_HINT: ClassVar[str] = "token_hint"
    API_BASE_URL: ClassVar[str] = "api_base_url"
    WEBHOOK_SECRET_ENCRYPTED: ClassVar[str] = "webhook_secret_encrypted"
    WEBHOOK_SECRET_HASH: ClassVar[str] = "webhook_secret_hash"
    WEBHOOK_URL: ClassVar[str] = "webhook_url"
    BOT_ID: ClassVar[str] = "bot_id"
    BOT_USERNAME: ClassVar[str] = "bot_username"
    BOT_DISPLAY_NAME: ClassVar[str] = "bot_display_name"
    IS_ENABLED: ClassVar[str] = "is_enabled"
    METADATA_JSON: ClassVar[str] = "metadata_json"
    LAST_VERIFIED_AT: ClassVar[str] = "last_verified_at"
    LAST_WEBHOOK_AT: ClassVar[str] = "last_webhook_at"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
    DELETED_AT: ClassVar[str] = "deleted_at"
