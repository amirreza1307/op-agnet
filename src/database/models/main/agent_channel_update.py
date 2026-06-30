from datetime import datetime
from typing import Any, Optional

from basalam.backbone_orm import ModelAbstract


class AgentChannelUpdate(ModelAbstract):
    id: int
    channel_id: int
    provider_update_id: int
    status: str = "processing"
    error_message: Optional[str] = None
    received_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    def repository(self) -> Any:
        from database.repositories.main.agent_channel_update_repo import (
            AgentChannelUpdateRepo,
        )

        return AgentChannelUpdateRepo
