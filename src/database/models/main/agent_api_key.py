from datetime import datetime
from typing import Any, Optional

from basalam.backbone_orm import ModelAbstract


class AgentApiKey(ModelAbstract):
    id: int
    node_id: int
    name: str
    key_prefix: str
    key_hash: str
    expires_at: datetime
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    def repository(self) -> Any:
        from database.repositories.main.agent_api_key_repo import AgentApiKeyRepo

        return AgentApiKeyRepo
