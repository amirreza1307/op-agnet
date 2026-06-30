from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from api.errors import BadRequestError, ConflictError, NotFoundError
from database.repositories.main.agent_channel_repo import AgentChannelRepo
from database.repositories.main.agent_node_repo import AgentNodeRepo
from services.platform.admin._shared import normalize_payload
from services.platform.channels.channel_crypto import ChannelCrypto
from services.platform.channels.constants import (
    DEFAULT_API_BASE_URLS,
    SUPPORTED_CHANNEL_TYPES,
)
from services.platform.channels.provider_client import BotProviderClient
from setup.config import config


class ChannelAdminService:
    @staticmethod
    def _validate_channel_type(channel_type: str) -> str:
        normalized = str(channel_type or "").strip().lower()
        if normalized not in SUPPORTED_CHANNEL_TYPES:
            raise BadRequestError(
                f"Unsupported channel_type. Expected one of: {sorted(SUPPORTED_CHANNEL_TYPES)}"
            )
        return normalized

    @staticmethod
    def _normalize_api_base_url(channel_type: str, value: str | None) -> str:
        url = (value or DEFAULT_API_BASE_URLS[channel_type]).strip().rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise BadRequestError("api_base_url must be a valid HTTPS URL")
        return url

    @staticmethod
    def _public_base_url(value: str | None) -> str:
        url = (value or config.CHANNEL_PUBLIC_BASE_URL or "").strip().rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise BadRequestError(
                "A valid HTTPS public_base_url is required to configure the webhook"
            )
        return url

    @staticmethod
    def serialize(channel: Any) -> dict[str, Any]:
        public_base = str(config.CHANNEL_PUBLIC_BASE_URL or "").strip()
        suggested_url = None
        if public_base:
            suggested_url = ChannelAdminService.build_webhook_url(channel, public_base)
        return {
            "id": channel.id,
            "node_id": channel.node_id,
            "channel_type": channel.channel_type,
            "name": channel.name,
            "token_hint": channel.token_hint,
            "api_base_url": channel.api_base_url,
            "webhook_url": channel.webhook_url,
            "suggested_webhook_url": suggested_url,
            "bot_id": channel.bot_id,
            "bot_username": channel.bot_username,
            "bot_display_name": channel.bot_display_name,
            "is_enabled": channel.is_enabled,
            "metadata_json": channel.metadata_json,
            "last_verified_at": channel.last_verified_at,
            "last_webhook_at": channel.last_webhook_at,
            "created_at": channel.created_at,
            "updated_at": channel.updated_at,
        }

    @staticmethod
    def build_webhook_url(channel: Any, public_base_url: str) -> str:
        base_url = public_base_url.rstrip("/")
        if channel.channel_type == "telegram":
            return f"{base_url}/v1/channels/telegram/webhook/{channel.id}"
        secret = ChannelCrypto.decrypt(channel.webhook_secret_encrypted)
        return f"{base_url}/v1/channels/bale/webhook/{channel.id}/{secret}"

    @staticmethod
    async def _get_or_raise(channel_id: int, *, enabled: bool = False):
        channel = (
            await AgentChannelRepo.find_enabled_by_id(channel_id)
            if enabled
            else await AgentChannelRepo.find_by_id(channel_id)
        )
        if channel is None:
            raise NotFoundError(f"Channel {channel_id} does not exist")
        return channel

    @staticmethod
    def _client(channel: Any) -> BotProviderClient:
        return BotProviderClient(
            token=ChannelCrypto.decrypt(channel.bot_token_encrypted),
            api_base_url=channel.api_base_url,
        )

    @classmethod
    async def create(cls, node_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        node = await AgentNodeRepo.find_active_by_id(node_id)
        if node is None:
            raise NotFoundError(f"Agent node {node_id} does not exist")

        channel_type = cls._validate_channel_type(payload["channel_type"])
        if await AgentChannelRepo.find_by_node_and_type(node_id, channel_type):
            raise ConflictError(
                f"Agent node {node_id} already has a {channel_type} channel"
            )

        token = payload["bot_token"].strip()
        if not token:
            raise BadRequestError("bot_token cannot be empty")
        token_hash = ChannelCrypto.digest(token)
        if await AgentChannelRepo.find_by_token_hash(token_hash):
            raise ConflictError("This bot token is already assigned to a channel")
        api_base_url = cls._normalize_api_base_url(
            channel_type, payload.get("api_base_url")
        )
        client = BotProviderClient(token=token, api_base_url=api_base_url)
        bot_info = await client.get_me() if payload.get("verify_bot", True) else {}
        secret = ChannelCrypto.generate_webhook_secret()

        record = await AgentChannelRepo.create_return(
            normalize_payload(
                "agent_channel",
                {
                    "node_id": node_id,
                    "channel_type": channel_type,
                    "name": payload.get("name")
                    or bot_info.get("username")
                    or f"{channel_type} bot",
                    "bot_token_encrypted": ChannelCrypto.encrypt(token),
                    "token_hash": token_hash,
                    "token_hint": ChannelCrypto.token_hint(token),
                    "api_base_url": api_base_url,
                    "webhook_secret_encrypted": ChannelCrypto.encrypt(secret),
                    "webhook_secret_hash": ChannelCrypto.digest(secret),
                    "bot_id": str(bot_info.get("id")) if bot_info.get("id") else None,
                    "bot_username": bot_info.get("username"),
                    "bot_display_name": bot_info.get("first_name"),
                    "is_enabled": payload.get("is_enabled", True),
                    "metadata_json": payload.get("metadata_json"),
                    "last_verified_at": (
                        datetime.now(timezone.utc) if bot_info else None
                    ),
                },
            )
        )
        return cls.serialize(record)

    @classmethod
    async def list_for_node(cls, node_id: int) -> list[dict[str, Any]]:
        return [
            cls.serialize(item)
            for item in await AgentChannelRepo.list_by_node_id(node_id)
        ]

    @classmethod
    async def get(cls, channel_id: int) -> dict[str, Any]:
        return cls.serialize(await cls._get_or_raise(channel_id))

    @classmethod
    async def update(
        cls, channel_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id)
        updates: dict[str, Any] = {}

        if "name" in payload:
            updates["name"] = payload["name"]
        if "is_enabled" in payload:
            updates["is_enabled"] = payload["is_enabled"]
        if "metadata_json" in payload:
            updates["metadata_json"] = payload["metadata_json"]

        token = None
        if "bot_token" in payload:
            token = (payload["bot_token"] or "").strip()
            if not token:
                raise BadRequestError("bot_token cannot be empty")
            token_hash = ChannelCrypto.digest(token)
            token_owner = await AgentChannelRepo.find_by_token_hash(token_hash)
            if token_owner is not None and token_owner.id != channel_id:
                raise ConflictError(
                    "This bot token is already assigned to another channel"
                )
            updates.update(
                {
                    "bot_token_encrypted": ChannelCrypto.encrypt(token),
                    "token_hash": token_hash,
                    "token_hint": ChannelCrypto.token_hint(token),
                }
            )

        api_base_url = channel.api_base_url
        if "api_base_url" in payload:
            api_base_url = cls._normalize_api_base_url(
                channel.channel_type, payload["api_base_url"]
            )
            updates["api_base_url"] = api_base_url

        if token is not None or "api_base_url" in payload:
            effective_token = token or ChannelCrypto.decrypt(
                channel.bot_token_encrypted
            )
            if payload.get("verify_bot", True):
                bot_info = await BotProviderClient(
                    token=effective_token, api_base_url=api_base_url
                ).get_me()
                updates.update(
                    {
                        "bot_id": (
                            str(bot_info.get("id")) if bot_info.get("id") else None
                        ),
                        "bot_username": bot_info.get("username"),
                        "bot_display_name": bot_info.get("first_name"),
                        "last_verified_at": datetime.now(timezone.utc),
                    }
                )

        if not updates:
            return cls.serialize(channel)
        updated = await AgentChannelRepo.update_by_id(
            channel_id,
            normalize_payload("agent_channel", updates),
            return_=True,
        )
        return cls.serialize(updated)

    @classmethod
    async def deactivate(cls, channel_id: int) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id)
        if channel.webhook_url:
            try:
                await cls._client(channel).delete_webhook()
            except Exception:
                # Deactivation must remain possible if the provider is down or
                # the old token has already been revoked.
                pass
        updated = await AgentChannelRepo.update_by_id(
            channel_id,
            {
                "is_enabled": False,
                "webhook_url": None,
            },
            return_=True,
        )
        return cls.serialize(updated)

    @classmethod
    async def verify(cls, channel_id: int) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id)
        bot_info = await cls._client(channel).get_me()
        updated = await AgentChannelRepo.update_by_id(
            channel_id,
            {
                "bot_id": str(bot_info.get("id")) if bot_info.get("id") else None,
                "bot_username": bot_info.get("username"),
                "bot_display_name": bot_info.get("first_name"),
                "last_verified_at": datetime.now(timezone.utc),
            },
            return_=True,
        )
        return {"ok": True, "channel": cls.serialize(updated), "bot": bot_info}

    @classmethod
    async def rotate_webhook_secret(cls, channel_id: int) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id)
        secret = ChannelCrypto.generate_webhook_secret()
        updated = await AgentChannelRepo.update_by_id(
            channel_id,
            {
                "webhook_secret_encrypted": ChannelCrypto.encrypt(secret),
                "webhook_secret_hash": ChannelCrypto.digest(secret),
                "webhook_url": None,
            },
            return_=True,
        )
        return cls.serialize(updated)

    @classmethod
    async def set_webhook(
        cls, channel_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id, enabled=True)
        public_base_url = cls._public_base_url(payload.get("public_base_url"))
        webhook_url = cls.build_webhook_url(channel, public_base_url)
        secret = ChannelCrypto.decrypt(channel.webhook_secret_encrypted)
        client = cls._client(channel)

        provider_kwargs: dict[str, Any] = {}
        if channel.channel_type == "telegram":
            provider_kwargs = {
                "secret_token": secret,
                "drop_pending_updates": payload.get(
                    "drop_pending_updates", False
                ),
                "allowed_updates": payload.get("allowed_updates"),
            }
        await client.set_webhook(url=webhook_url, **provider_kwargs)
        updated = await AgentChannelRepo.update_by_id(
            channel_id,
            {
                "webhook_url": webhook_url,
                "last_webhook_at": datetime.now(timezone.utc),
            },
            return_=True,
        )
        return {
            "ok": True,
            "webhook_url": webhook_url,
            "channel": cls.serialize(updated),
        }

    @classmethod
    async def delete_webhook(
        cls, channel_id: int, *, drop_pending_updates: bool = False
    ) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id)
        client = cls._client(channel)
        await client.delete_webhook(
            drop_pending_updates=(
                drop_pending_updates if channel.channel_type == "telegram" else False
            )
        )
        updated = await AgentChannelRepo.update_by_id(
            channel_id, {"webhook_url": None}, return_=True
        )
        return {"ok": True, "channel": cls.serialize(updated)}

    @classmethod
    async def get_webhook_info(cls, channel_id: int) -> dict[str, Any]:
        channel = await cls._get_or_raise(channel_id)
        info = await cls._client(channel).get_webhook_info()
        return {"ok": True, "channel": cls.serialize(channel), "webhook": info}
