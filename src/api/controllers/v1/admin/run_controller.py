from api.controllers.controller_abstract import ControllerAbstract
from api.request_models.v1.admin.admin_request_models import PlatformAdminRunRequestModel
from services.platform.runtime.execution.platform_run_service import PlatformRunService


class RunController(ControllerAbstract):

    async def run(self, request_model: PlatformAdminRunRequestModel):
        return await PlatformRunService.run(
            node_id=request_model.node_id,
            slug=request_model.slug,
            message=request_model.message,
            session_id=request_model.session_id,
            principal_id=request_model.principal_id or "admin",
            context=request_model.context,
            instructions=request_model.instructions,
            stream_events=request_model.stream_events,
            output_schema=request_model.output_schema,
            structured_outputs=request_model.structured_outputs,
        )

