from typing import Any, Optional

from api.errors import BadRequestError, NotFoundError
from database.repositories.main.tool_knowledge_node_repo import ToolKnowledgeNodeRepo
from database.repositories.main.tool_repo import ToolRepo
from tools.registry import has_slug


class ToolKnowledgeNodeAdmin:
    @staticmethod
    async def _validate_tool_slug(tool_slug: str) -> str:
        normalized = (tool_slug or "").strip()
        if has_slug(normalized):
            return normalized
        tool = await ToolRepo.find_active_by_slug(normalized)
        if tool is None:
            raise BadRequestError(f"Unknown tool slug '{normalized}'")
        return normalized

    @staticmethod
    def _normalize_text(value: Any, field_name: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise BadRequestError(f"{field_name} must not be empty")
        return normalized

    @classmethod
    async def create(cls, payload: dict[str, Any]):
        payload = dict(payload)
        payload["tool_slug"] = await cls._validate_tool_slug(payload["tool_slug"])
        payload["title"] = cls._normalize_text(payload["title"], "title")
        payload["content"] = cls._normalize_text(payload["content"], "content")
        return await ToolKnowledgeNodeRepo.create_return(payload)

    @staticmethod
    async def list(
        *,
        tool_slug: Optional[str] = None,
        include_inactive: bool = False,
        search: Optional[str] = None,
    ):
        nodes = await ToolKnowledgeNodeRepo.list_nodes(
            tool_slug=(tool_slug or "").strip() or None,
            include_inactive=include_inactive,
        )
        query = (search or "").strip().lower()
        if not query:
            return nodes
        return [
            node
            for node in nodes
            if query in node.title.lower()
            or query in node.content.lower()
            or query in node.tool_slug.lower()
        ]

    @staticmethod
    async def get(knowledge_node_id: int):
        node = await ToolKnowledgeNodeRepo.find_by_id(knowledge_node_id)
        if node is None:
            raise NotFoundError(
                f"Tool knowledge node {knowledge_node_id} does not exist"
            )
        return node

    @classmethod
    async def update(cls, knowledge_node_id: int, payload: dict[str, Any]):
        current = await ToolKnowledgeNodeRepo.find_by_id(knowledge_node_id)
        if current is None:
            raise NotFoundError(
                f"Tool knowledge node {knowledge_node_id} does not exist"
        )
        payload = dict(payload)
        if "tool_slug" in payload:
            payload["tool_slug"] = await cls._validate_tool_slug(payload["tool_slug"])
        if "title" in payload:
            payload["title"] = cls._normalize_text(payload["title"], "title")
        if "content" in payload:
            payload["content"] = cls._normalize_text(
                payload["content"], "content"
            )
        if not payload:
            return current
        return await ToolKnowledgeNodeRepo.update_by_id(
            knowledge_node_id, payload, return_=True
        )

    @staticmethod
    async def deactivate(knowledge_node_id: int):
        current = await ToolKnowledgeNodeRepo.find_active_by_id(knowledge_node_id)
        if current is None:
            raise NotFoundError(
                f"Tool knowledge node {knowledge_node_id} does not exist"
            )
        return await ToolKnowledgeNodeRepo.update_by_id(
            knowledge_node_id, {"is_active": False}, return_=True
        )
