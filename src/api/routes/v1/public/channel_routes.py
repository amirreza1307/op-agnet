from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header

from services.platform.channels.channel_webhook_service import (
    ChannelWebhookService,
)

router = APIRouter(prefix="/v1/channels", tags=["Agent Channels"])


@router.post("/telegram/webhook/{channel_id}")
async def receive_telegram_webhook(
    channel_id: int,
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    telegram_secret: str | None = Header(
        default=None, alias="X-Telegram-Bot-Api-Secret-Token"
    ),
):
    channel, claimed = await ChannelWebhookService.accept(
        channel_type="telegram",
        channel_id=channel_id,
        webhook_secret=None,
        telegram_secret_header=telegram_secret,
        update=update,
    )
    if claimed is not None:
        background_tasks.add_task(
            ChannelWebhookService.process_isolated,
            channel_id=channel.id,
            update_record_id=claimed.id,
            update=update,
        )
    return {"ok": True}


@router.post("/bale/webhook/{channel_id}/{webhook_secret}")
async def receive_bale_webhook(
    channel_id: int,
    webhook_secret: str,
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
):
    channel, claimed = await ChannelWebhookService.accept(
        channel_type="bale",
        channel_id=channel_id,
        webhook_secret=webhook_secret,
        telegram_secret_header=None,
        update=update,
    )
    if claimed is not None:
        background_tasks.add_task(
            ChannelWebhookService.process_isolated,
            channel_id=channel.id,
            update_record_id=claimed.id,
            update=update,
        )
    return {"ok": True}
