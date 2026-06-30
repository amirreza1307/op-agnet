import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class McpServer(ModelAbstract):
    id: int
    slug: str
    name: str
    transport: str
    command: Optional[str] = None
    url: Optional[str] = None
    working_directory: Optional[str] = None
    env_json: Optional[Dict[str, str]] = None
    headers_json: Optional[Dict[str, Any]] = None
    include_tools_json: Optional[List[str]] = None
    exclude_tools_json: Optional[List[str]] = None
    tool_name_prefix: Optional[str] = None
    timeout_seconds: int = 15
    refresh_connection: bool = False
    allow_partial_failure: bool = False
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    @field_validator(
        "env_json",
        "headers_json",
        "include_tools_json",
        "exclude_tools_json",
        "metadata_json",
        mode="before",
    )
    @classmethod
    def parse_json_field(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    def repository(self) -> Any:
        from database.repositories.main.mcp_server_repo import McpServerRepo

        return McpServerRepo
