import json
from typing import Any, Dict, List, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class AgnoSession(ModelAbstract):
    session_id: str
    user_id: Optional[str] = None
    workflow_id: Optional[str] = None
    team_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_type: str = ""
    session_data: Optional[Dict] = None
    agent_data: Optional[Dict] = None
    summary: Optional[Dict] = None
    runs: Optional[List] = None
    metadata: Optional[Dict] = None
    workflow_data: Optional[Dict] = None
    team_data: Optional[Dict] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    x_ref: Optional[str] = None

    @field_validator(
        "session_data",
        "agent_data",
        "summary",
        "metadata",
        "workflow_data",
        "team_data",
        mode="before",
    )
    @classmethod
    def parse_json_dict(cls, v: Any) -> Optional[Dict]:
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else None
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @field_validator("runs", mode="before")
    @classmethod
    def parse_json_list(cls, v: Any) -> Optional[List]:
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [parsed]
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    def repository(self) -> Any:
        from database.repositories.agno.agno_session_repo import AgnoSessionRepo

        return AgnoSessionRepo
