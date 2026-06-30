from fastapi import APIRouter

from api.controllers.v1.admin.channel_controller import ChannelController
from api.request_models.v1.admin.admin_request_models import (
    AgentChannelCreateRequestModel,
    AgentChannelSetWebhookRequestModel,
    AgentChannelUpdateRequestModel,
)
from api.response_models.v1.admin.admin_response_models import (
    AgentChannelOperationResponseModel,
    AgentChannelResponseModel,
)

router = APIRouter(prefix="/v1/admin", tags=["Platform Admin - Channels"])


@router.post(
    "/nodes/{node_id}/channels", response_model=AgentChannelResponseModel
)
async def create_channel(
    node_id: int, request_data: AgentChannelCreateRequestModel
):
    return await ChannelController().create(node_id, request_data)


@router.get(
    "/nodes/{node_id}/channels", response_model=list[AgentChannelResponseModel]
)
async def list_node_channels(node_id: int):
    return await ChannelController().list_for_node(node_id)


@router.get("/channels/{channel_id}", response_model=AgentChannelResponseModel)
async def get_channel(channel_id: int):
    return await ChannelController().get(channel_id)


@router.patch("/channels/{channel_id}", response_model=AgentChannelResponseModel)
async def update_channel(
    channel_id: int, request_data: AgentChannelUpdateRequestModel
):
    return await ChannelController().update(channel_id, request_data)


@router.delete(
    "/channels/{channel_id}", response_model=AgentChannelResponseModel
)
async def deactivate_channel(channel_id: int):
    return await ChannelController().deactivate(channel_id)


@router.post(
    "/channels/{channel_id}/verify",
    response_model=AgentChannelOperationResponseModel,
)
async def verify_channel(channel_id: int):
    return await ChannelController().verify(channel_id)


@router.post(
    "/channels/{channel_id}/webhook/rotate-secret",
    response_model=AgentChannelResponseModel,
)
async def rotate_channel_webhook_secret(channel_id: int):
    return await ChannelController().rotate_webhook_secret(channel_id)


@router.post(
    "/channels/{channel_id}/webhook",
    response_model=AgentChannelOperationResponseModel,
)
async def set_channel_webhook(
    channel_id: int, request_data: AgentChannelSetWebhookRequestModel
):
    return await ChannelController().set_webhook(channel_id, request_data)


@router.delete(
    "/channels/{channel_id}/webhook",
    response_model=AgentChannelOperationResponseModel,
)
async def delete_channel_webhook(
    channel_id: int, drop_pending_updates: bool = False
):
    return await ChannelController().delete_webhook(
        channel_id, drop_pending_updates
    )


@router.get(
    "/channels/{channel_id}/webhook",
    response_model=AgentChannelOperationResponseModel,
)
async def get_channel_webhook_info(channel_id: int):
    return await ChannelController().get_webhook_info(channel_id)
