from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from api.errors import BadRequestError, NotFoundError
from database.repositories.main.agent_api_key_repo import AgentApiKeyRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from services.platform.auth.agent_api_key_material import generate_agent_api_key


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "node_id": record.node_id,
        "name": record.name,
        "key_prefix": record.key_prefix,
        "expires_at": record.expires_at,
        "is_active": record.is_active,
        "last_used_at": record.last_used_at,
        "revoked_at": record.revoked_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


class AgentApiKeyAdminService:
    @staticmethod
    async def create(
        node_id: int,
        *,
        name: str,
        expires_at: datetime,
    ) -> dict[str, Any]:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        if node is None:
            raise NotFoundError(f"Node {node_id} does not exist")

        normalized_expiry = _as_utc(expires_at)
        if normalized_expiry <= datetime.now(timezone.utc):
            raise BadRequestError("expires_at must be in the future")

        api_key, key_prefix, key_hash = generate_agent_api_key()
        record = await AgentApiKeyRepo.create_return(
            {
                "node_id": node_id,
                "name": name.strip(),
                "key_prefix": key_prefix,
                "key_hash": key_hash,
                "expires_at": normalized_expiry,
                "is_active": True,
            }
        )
        return {**_serialize_record(record), "api_key": api_key}

    @staticmethod
    async def list(node_id: int) -> list[dict[str, Any]]:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        if node is None:
            raise NotFoundError(f"Node {node_id} does not exist")
        return [
            _serialize_record(record)
            for record in await AgentApiKeyRepo.list_by_node_id(node_id)
        ]

    @staticmethod
    async def revoke(node_id: int, key_id: int) -> dict[str, Any]:
        record = await AgentApiKeyRepo.find_by_id_and_node(key_id, node_id)
        if record is None:
            raise NotFoundError(f"Agent API key {key_id} does not exist")

        if record.is_active:
            record = await AgentApiKeyRepo.update_by_id(
                key_id,
                {
                    "is_active": False,
                    "revoked_at": datetime.now(timezone.utc),
                },
                return_=True,
            )
        return _serialize_record(record)
