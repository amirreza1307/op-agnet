from datetime import datetime
from typing import Optional

from basalam.backbone_orm import ModelAbstract


class MessageFeedback(ModelAbstract):
    x_ref: Optional[str] = None
    id: int
    vendor_id: int
    user_id: Optional[int] = None
    session_id: str
    message_id: str
    is_positive: bool
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def repository(self):
        from database.repositories.main.message_feedback_repo import (
            MessageFeedbackRepo,
        )
        return MessageFeedbackRepo
