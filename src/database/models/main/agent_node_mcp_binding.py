import json
from datetime import datetime
from typing import Any, Dict, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class AgentNodeMcpBinding(ModelAbstract):
    id: int
    node_id: int
    mcp_server_id: int
    priority: int = 0
    is_enabled: bool = True
    binding_mode: Optional[str] = None
    header_template_json: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator("header_template_json", "metadata_json", mode="before")
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    def repository(self) -> Any:
        from database.repositories.main.agent_node_mcp_binding_repo import AgentNodeMcpBindingRepo

        return AgentNodeMcpBindingRepo
