import json
from datetime import datetime
from typing import Any, Dict, Optional

from basalam.backbone_orm import ModelAbstract
from pydantic import field_validator


class SkillPackage(ModelAbstract):
    id: int
    slug: str
    name: str
    description: str = ""
    source_path: str
    metadata_json: Optional[Dict[str, Any]] = None
    is_active: bool = True
    is_public: bool = False
    public_name: Optional[str] = None
    created_by: Optional[int] = None
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
        from database.repositories.main.skill_package_repo import SkillPackageRepo

        return SkillPackageRepo
