from __future__ import annotations

from datetime import datetime, timezone

from api.errors import ForbiddenError, UnauthorizedError
from database.repositories.main.agent_api_key_repo import AgentApiKeyRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from services.platform.auth.agent_api_key_material import hash_agent_api_key
from services.platform.auth.models import AgentApiKeyPrincipal


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AgentApiKeyAuthService:
    @staticmethod
    async def authenticate(api_key: str) -> AgentApiKeyPrincipal:
        normalized_key = str(api_key or "").strip()
        if not normalized_key or len(normalized_key) > 512:
            raise UnauthorizedError("Invalid or expired agent API key")

        record = await AgentApiKeyRepo.find_active_by_hash(
            hash_agent_api_key(normalized_key)
        )
        now = datetime.now(timezone.utc)
        if record is None or _utc_datetime(record.expires_at) <= now:
            raise UnauthorizedError("Invalid or expired agent API key")

        return AgentApiKeyPrincipal(
            key_id=record.id,
            node_id=record.node_id,
            key_prefix=record.key_prefix,
            expires_at=_utc_datetime(record.expires_at),
        )

    @staticmethod
    async def authorize_for_node(
        principal: AgentApiKeyPrincipal,
        *,
        node_id: int | None,
        slug: str | None,
    ) -> None:
        if node_id is not None:
            requested_node = await AgentNodeRepo.find_active_by_id(node_id)
        else:
            requested_node = await AgentNodeRepo.find_active_by_slug(str(slug or ""))

        if requested_node is None or requested_node.id != principal.node_id:
            raise ForbiddenError(
                "Agent API key is not authorized for the requested agent"
            )

        await AgentApiKeyRepo.update_by_id(
            principal.key_id,
            {"last_used_at": datetime.now(timezone.utc)},
            return_=False,
        )
