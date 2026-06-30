from api.controllers.controller_abstract import ControllerAbstract
from api.request_models.v1.admin.agent_api_key_request_models import (
    AgentApiKeyCreateRequestModel,
)
from services.platform.admin.api_keys.agent_api_key_admin_service import (
    AgentApiKeyAdminService,
)


class AgentApiKeyController(ControllerAbstract):
    async def create(
        self, node_id: int, request_model: AgentApiKeyCreateRequestModel
    ):
        return await AgentApiKeyAdminService.create(
            node_id,
            name=request_model.name,
            expires_at=request_model.expires_at,
        )

    async def list(self, node_id: int):
        return await AgentApiKeyAdminService.list(node_id)

    async def revoke(self, node_id: int, key_id: int):
        return await AgentApiKeyAdminService.revoke(node_id, key_id)
