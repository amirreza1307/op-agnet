from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class AgentChannelUpdateSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = "id"
    CHANNEL_ID: ClassVar[str] = "channel_id"
    PROVIDER_UPDATE_ID: ClassVar[str] = "provider_update_id"
    STATUS: ClassVar[str] = "status"
    ERROR_MESSAGE: ClassVar[str] = "error_message"
    RECEIVED_AT: ClassVar[str] = "received_at"
    PROCESSED_AT: ClassVar[str] = "processed_at"
    CREATED_AT: ClassVar[str] = "created_at"
    UPDATED_AT: ClassVar[str] = "updated_at"
