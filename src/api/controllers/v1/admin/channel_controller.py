from api.controllers.controller_abstract import ControllerAbstract
from api.request_models.v1.admin.admin_request_models import (
    AgentChannelCreateRequestModel,
    AgentChannelSetWebhookRequestModel,
    AgentChannelUpdateRequestModel,
)
from services.platform.channels.channel_admin_service import ChannelAdminService


class ChannelController(ControllerAbstract):
    async def create(
        self, node_id: int, request_model: AgentChannelCreateRequestModel
    ):
        return await ChannelAdminService.create(
            node_id, request_model.model_dump(exclude_none=True)
        )

    async def list_for_node(self, node_id: int):
        return await ChannelAdminService.list_for_node(node_id)

    async def get(self, channel_id: int):
        return await ChannelAdminService.get(channel_id)

    async def update(
        self, channel_id: int, request_model: AgentChannelUpdateRequestModel
    ):
        return await ChannelAdminService.update(
            channel_id, request_model.model_dump(exclude_unset=True)
        )

    async def deactivate(self, channel_id: int):
        return await ChannelAdminService.deactivate(channel_id)

    async def verify(self, channel_id: int):
        return await ChannelAdminService.verify(channel_id)

    async def rotate_webhook_secret(self, channel_id: int):
        return await ChannelAdminService.rotate_webhook_secret(channel_id)

    async def set_webhook(
        self, channel_id: int, request_model: AgentChannelSetWebhookRequestModel
    ):
        return await ChannelAdminService.set_webhook(
            channel_id, request_model.model_dump(exclude_none=True)
        )

    async def delete_webhook(
        self, channel_id: int, drop_pending_updates: bool = False
    ):
        return await ChannelAdminService.delete_webhook(
            channel_id, drop_pending_updates=drop_pending_updates
        )

    async def get_webhook_info(self, channel_id: int):
        return await ChannelAdminService.get_webhook_info(channel_id)
