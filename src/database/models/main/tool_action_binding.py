import json
from datetime import datetime
from typing import Any, Dict, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class ToolActionBinding(ModelAbstract):
    id: int
    tool_id: int
    action_id: int
    constructor_params: Dict = {}
    response_title: Optional[str] = None
    priority: int = 0
    is_enabled: bool = True
    metadata_json: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator("constructor_params", "metadata_json", mode="before")
    @classmethod
    def parse_json_field(cls, value: Any):
        if isinstance(value, str):
            return json.loads(value)
        return value

    def repository(self) -> Any:
        from database.repositories.main.tool_action_binding_repo import ToolActionBindingRepo

        return ToolActionBindingRepo
