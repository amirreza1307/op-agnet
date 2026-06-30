from fastapi import APIRouter, status

from api.controllers.v1.admin.agent_api_key_controller import (
    AgentApiKeyController,
)
from api.request_models.v1.admin.agent_api_key_request_models import (
    AgentApiKeyCreateRequestModel,
)
from api.response_models.v1.admin.agent_api_key_response_models import (
    AgentApiKeyCreatedResponseModel,
    AgentApiKeyResponseModel,
)


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin"])


@router.post(
    "/nodes/{node_id}/api-keys",
    response_model=AgentApiKeyCreatedResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_api_key(
    node_id: int, request_data: AgentApiKeyCreateRequestModel
):
    return await AgentApiKeyController().create(node_id, request_data)


@router.get(
    "/nodes/{node_id}/api-keys",
    response_model=list[AgentApiKeyResponseModel],
)
async def list_agent_api_keys(node_id: int):
    return await AgentApiKeyController().list(node_id)


@router.delete(
    "/nodes/{node_id}/api-keys/{key_id}",
    response_model=AgentApiKeyResponseModel,
)
async def revoke_agent_api_key(node_id: int, key_id: int):
    return await AgentApiKeyController().revoke(node_id, key_id)
