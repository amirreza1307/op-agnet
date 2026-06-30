from __future__ import annotations

import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request

from api.errors import NotFoundError, UnauthorizedError
from database.repositories.main.agent_channel_repo import AgentChannelRepo
from database.repositories.main.agent_channel_update_repo import (
    AgentChannelUpdateRepo,
)
from services.platform.channels.channel_crypto import ChannelCrypto
from services.platform.channels.constants import SUPPORTED_CHANNEL_TYPES
from services.platform.channels.provider_client import BotProviderClient
from services.platform.runtime.execution.platform_run_service import (
    PlatformRunService,
)
from setup.config import config
from setup.dbs.postgres import release_all_postgres_connections
from setup.request_context import RequestContext

logger = logging.getLogger(__name__)


class ChannelWebhookService:
    @classmethod
    async def process_isolated(
        cls,
        *,
        channel_id: int,
        update_record_id: int,
        update: dict[str, Any],
    ) -> None:
        # Starlette runs BackgroundTasks after the response body has been sent.
        # The request middleware has already released its DB connection at that
        # point, so give channel processing its own request-context key and
        # explicitly release every connection it acquires.
        background_request = Request(
            {
                "type": "http",
                "method": "POST",
                "scheme": "https",
                "path": "/internal/channel-background",
                "raw_path": b"/internal/channel-background",
                "query_string": b"",
                "headers": [],
                "client": None,
                "server": None,
            }
        )
        with RequestContext(background_request):
            try:
                await cls.process(
                    channel_id=channel_id,
                    update_record_id=update_record_id,
                    update=update,
                )
            finally:
                await release_all_postgres_connections()

    @classmethod
    async def accept(
        cls,
        *,
        channel_type: str,
        channel_id: int,
        webhook_secret: str | None,
        telegram_secret_header: str | None,
        update: dict[str, Any],
    ) -> tuple[Any, Any | None]:
        if channel_type not in SUPPORTED_CHANNEL_TYPES:
            raise NotFoundError("Channel not found")
        channel = await AgentChannelRepo.find_enabled_by_id(channel_id)
        if channel is None or channel.channel_type != channel_type:
            raise NotFoundError("Channel not found")

        if channel_type == "telegram":
            expected_secret = ChannelCrypto.decrypt(
                channel.webhook_secret_encrypted
            )
            if not telegram_secret_header or not hmac.compare_digest(
                telegram_secret_header, expected_secret
            ):
                raise UnauthorizedError("Invalid Telegram webhook secret")
        else:
            if not webhook_secret or not hmac.compare_digest(
                ChannelCrypto.digest(webhook_secret),
                channel.webhook_secret_hash,
            ):
                raise NotFoundError("Channel not found")

        update_id = update.get("update_id")
        if isinstance(update_id, bool) or not isinstance(update_id, int):
            raise UnauthorizedError("Webhook update_id is missing or invalid")

        claimed = await AgentChannelUpdateRepo.claim(channel.id, update_id)
        return channel, claimed

    @classmethod
    async def process(
        cls,
        *,
        channel_id: int,
        update_record_id: int,
        update: dict[str, Any],
    ) -> None:
        channel = await AgentChannelRepo.find_enabled_by_id(channel_id)
        if channel is None:
            await cls._mark_failed(update_record_id, "Channel is disabled")
            return

        message = update.get("message")
        if not isinstance(message, dict):
            await cls._mark_completed(update_record_id)
            return

        sender = message.get("from") or {}
        if sender.get("is_bot"):
            await cls._mark_completed(update_record_id)
            return

        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = message.get("text") or message.get("caption")
        if chat_id is None:
            await cls._mark_failed(update_record_id, "Message chat.id is missing")
            return

        client = BotProviderClient(
            token=ChannelCrypto.decrypt(channel.bot_token_encrypted),
            api_base_url=channel.api_base_url,
        )

        if not isinstance(text, str) or not text.strip():
            try:
                await client.send_message(
                    chat_id=chat_id,
                    text="در حال حاضر فقط پیام متنی پشتیبانی می‌شود.",
                )
                await cls._mark_completed(update_record_id)
            except Exception as exc:
                await cls._mark_failed(update_record_id, str(exc))
            return

        try:
            try:
                await client.send_chat_action(chat_id=chat_id)
            except Exception:
                logger.debug("channel typing action failed", exc_info=True)

            user_id = sender.get("id") or chat_id
            session_id = f"{channel.channel_type}:{channel.id}:{chat_id}"
            principal_id = f"{channel.channel_type}:{user_id}"
            result = await PlatformRunService.run(
                node_id=channel.node_id,
                message=text.strip(),
                session_id=session_id,
                principal_id=principal_id,
                context={
                    "channel": {
                        "type": channel.channel_type,
                        "channel_id": channel.id,
                        "chat": {
                            "id": chat_id,
                            "type": chat.get("type"),
                            "title": chat.get("title"),
                            "username": chat.get("username"),
                        },
                        "user": {
                            "id": sender.get("id"),
                            "username": sender.get("username"),
                            "first_name": sender.get("first_name"),
                            "last_name": sender.get("last_name"),
                            "language_code": sender.get("language_code"),
                        },
                        "message_id": message.get("message_id"),
                        "update_id": update.get("update_id"),
                    }
                },
            )
            response_text = cls._content_to_text(result.get("content"))
            for chunk in cls._split_message(response_text):
                await client.send_message(chat_id=chat_id, text=chunk)
            await cls._mark_completed(update_record_id)
        except Exception as exc:
            logger.exception(
                "channel update failed channel_id=%s update_id=%s",
                channel.id,
                update.get("update_id"),
            )
            await cls._mark_failed(update_record_id, str(exc))
            try:
                await client.send_message(
                    chat_id=chat_id, text=config.CHANNEL_ERROR_MESSAGE
                )
            except Exception:
                logger.exception("channel error message delivery failed")

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if content is None:
            return "پاسخی برای ارسال تولید نشد."
        if isinstance(content, str):
            return content.strip() or "پاسخی برای ارسال تولید نشد."
        return json.dumps(content, ensure_ascii=False, default=str, indent=2)

    @staticmethod
    def _split_message(text: str, limit: int = 4000) -> list[str]:
        text = text.strip()
        if len(text) <= limit:
            return [text]
        chunks: list[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= limit:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, limit)
            if split_at < limit // 2:
                split_at = remaining.rfind(" ", 0, limit)
            if split_at < limit // 2:
                split_at = limit
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        return [chunk for chunk in chunks if chunk]

    @staticmethod
    async def _mark_completed(update_record_id: int) -> None:
        await AgentChannelUpdateRepo.update_by_id(
            update_record_id,
            {
                "status": "completed",
                "processed_at": datetime.now(timezone.utc),
            },
        )

    @staticmethod
    async def _mark_failed(update_record_id: int, error: str) -> None:
        await AgentChannelUpdateRepo.update_by_id(
            update_record_id,
            {
                "status": "failed",
                "error_message": error[:2000],
                "processed_at": datetime.now(timezone.utc),
            },
        )
