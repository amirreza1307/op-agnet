import json
from datetime import datetime
from typing import Any, Optional, Dict, List
from pydantic import field_validator, model_validator
from basalam.backbone_orm import ModelAbstract


class Tool(ModelAbstract):
    id: int
    slug: Optional[str] = None
    name: str
    description: str
    progress_label: Optional[str] = None
    progress_visual_type: Optional[str] = None
    progress_visual_value: Optional[str] = None
    tool_type: str
    user_types: List[str] = []
    parameters: List[Dict] = []
    required_tool_ids: List[int] = []
    show_result: bool = False
    action_only_name: Optional[str] = None
    action_only_description: Optional[str] = None
    rule_method: Optional[str] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    agent_id: Optional[int] = None
    api_url: Optional[str] = None
    api_method: str = "GET"
    api_headers: Optional[Dict] = None
    api_body_template: Optional[str] = None
    metadata_json: Optional[Dict] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @staticmethod
    def _parse_json_like_list(value: Any) -> Any:
        parsed = value
        for _ in range(2):
            if not isinstance(parsed, str):
                break
            raw = parsed.strip()
            if not raw:
                return []
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError, ValueError):
                return value
        return parsed

    @model_validator(mode='before')
    @classmethod
    def normalize_json_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        for field_name in ("user_types", "parameters", "required_tool_ids", "api_headers", "metadata_json"):
            normalized[field_name] = cls._parse_json_like_list(normalized.get(field_name))
        return normalized

    @field_validator("user_types", "parameters", "required_tool_ids", "api_headers", "metadata_json", mode="before")
    @classmethod
    def parse_json_field(cls, v):
        return cls._parse_json_like_list(v)

    def repository(self) -> Any:
        from database.repositories.main.tool_repo import ToolRepo
        return ToolRepo
