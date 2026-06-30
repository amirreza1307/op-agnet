from api.controllers.controller_abstract import ControllerAbstract
from api.dependencies import AgentApiKeyPrincipal
from api.request_models.v1.public.run_request_models import PlatformRunRequestModel
from services.platform.auth.agent_api_key_auth_service import AgentApiKeyAuthService
from services.platform.runtime.execution.platform_run_service import PlatformRunService


class PlatformRunController(ControllerAbstract):

    async def run(
        self,
        request_model: PlatformRunRequestModel,
        api_key_principal: AgentApiKeyPrincipal,
    ):
        await AgentApiKeyAuthService.authorize_for_node(
            api_key_principal,
            node_id=request_model.node_id,
            slug=request_model.slug,
        )
        return await PlatformRunService.run(
            node_id=request_model.node_id,
            slug=request_model.slug,
            message=request_model.message,
            session_id=request_model.session_id,
            principal_id=request_model.principal_id or "anonymous",
            context=request_model.context,
            instructions=request_model.instructions,
            output_schema=request_model.output_schema,
            structured_outputs=request_model.structured_outputs,
            forwarded_auth_headers={},
        )
