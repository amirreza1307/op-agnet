from datetime import datetime
from typing import Any, Optional

from basalam.backbone_orm import ModelAbstract


class ToolKnowledgeNode(ModelAbstract):
    id: int
    tool_slug: str
    title: str
    content: str
    priority: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    x_ref: Optional[str] = None

    def repository(self) -> Any:
        from database.repositories.main.tool_knowledge_node_repo import (
            ToolKnowledgeNodeRepo,
        )

        return ToolKnowledgeNodeRepo
