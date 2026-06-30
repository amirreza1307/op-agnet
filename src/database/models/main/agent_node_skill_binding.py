import json
from datetime import datetime
from typing import Any, Dict, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class AgentNodeSkillBinding(ModelAbstract):
    id: int
    node_id: int
    skill_package_id: int
    priority: int = 0
    is_enabled: bool = True
    metadata_json: Optional[Dict[str, Any]] = None
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
        from database.repositories.main.agent_node_skill_binding_repo import AgentNodeSkillBindingRepo

        return AgentNodeSkillBindingRepo
