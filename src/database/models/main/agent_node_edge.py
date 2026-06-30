import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class AgentNodeEdge(ModelAbstract):
    id: int
    parent_node_id: int
    child_node_id: int
    priority: int = 0
    is_active: bool = True
    member_instructions_json: List[str] = []
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator("member_instructions_json", "metadata_json", mode="before")
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    def repository(self) -> Any:
        from database.repositories.main.agent_node_edge_repo import AgentNodeEdgeRepo

        return AgentNodeEdgeRepo
