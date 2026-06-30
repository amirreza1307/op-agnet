from typing import ClassVar

from basalam.backbone_orm import ModelSchemaAbstract


class MessageFeedbackSchema(ModelSchemaAbstract):
    ID: ClassVar[str] = 'id'
    VENDOR_ID: ClassVar[str] = 'vendor_id'
    USER_ID: ClassVar[str] = 'user_id'
    SESSION_ID: ClassVar[str] = 'session_id'
    MESSAGE_ID: ClassVar[str] = 'message_id'
    IS_POSITIVE: ClassVar[str] = 'is_positive'
    COMMENT: ClassVar[str] = 'comment'
    CREATED_AT: ClassVar[str] = 'created_at'
    UPDATED_AT: ClassVar[str] = 'updated_at'
