import json
from datetime import datetime
from typing import Any, Dict, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class AgentChannel(ModelAbstract):
    id: int
    node_id: int
    channel_type: str
    name: str
    bot_token_encrypted: str
    token_hash: str
    token_hint: str
    api_base_url: str
    webhook_secret_encrypted: str
    webhook_secret_hash: str
    webhook_url: Optional[str] = None
    bot_id: Optional[str] = None
    bot_username: Optional[str] = None
    bot_display_name: Optional[str] = None
    is_enabled: bool = True
    metadata_json: Optional[Dict[str, Any]] = None
    last_verified_at: Optional[datetime] = None
    last_webhook_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator("metadata_json", mode="before")
    @classmethod
    def parse_json_field(cls, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

    def repository(self) -> Any:
        from database.repositories.main.agent_channel_repo import AgentChannelRepo

        return AgentChannelRepo
