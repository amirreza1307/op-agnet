from fastapi import APIRouter, Depends

from api.controllers.v1.public.agent_controller import PlatformRunController
from api.dependencies import AgentApiKeyPrincipal, require_agent_api_key
from api.request_models.v1.public.run_request_models import PlatformRunRequestModel
from api.response_models.v1.public.run_response_models import PlatformRunResponseModel


router = APIRouter(prefix="/v1", tags=["Agent"])


@router.post("/agent/run", response_model=PlatformRunResponseModel)
async def run_agent(
    request_data: PlatformRunRequestModel,
    api_key_principal: AgentApiKeyPrincipal = Depends(require_agent_api_key),
):
    return await PlatformRunController().run(request_data, api_key_principal)
