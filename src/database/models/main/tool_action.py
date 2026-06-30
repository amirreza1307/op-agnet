import json
from datetime import datetime
from typing import Any, Optional, Dict
from pydantic import field_validator
from basalam.backbone_orm import ModelAbstract


class ToolAction(ModelAbstract):
    id: int
    tool_id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None
    description: str = ""
    fa_name: Optional[str] = None
    fa_description: Optional[str] = None
    constructor_params: Dict = {}
    response_title: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    metadata_json: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator('constructor_params', 'metadata_json', mode='before')
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    def repository(self) -> Any:
        from database.repositories.main.tool_action_repo import ToolActionRepo
        return ToolActionRepo
