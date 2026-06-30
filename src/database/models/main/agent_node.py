import json
from datetime import datetime
from typing import Any, Dict, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class AgentNode(ModelAbstract):
    id: int
    slug: str
    name: str
    description: str = ""
    system_prompt: str = ""
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_api_key: Optional[str] = None
    model_base_url: Optional[str] = None
    session_table: Optional[str] = None
    runtime_config_json: Optional[Dict[str, Any]] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    image_file_id: Optional[int] = None
    priority: int = 0
    version: int = 1
    metadata_json: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator("runtime_config_json", "metadata_json", mode="before")
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    def repository(self) -> Any:
        from database.repositories.main.agent_node_repo import AgentNodeRepo

        return AgentNodeRepo
