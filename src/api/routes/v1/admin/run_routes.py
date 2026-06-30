from fastapi import APIRouter

from api.controllers.v1.admin.run_controller import RunController
from api.request_models.v1.admin.admin_request_models import PlatformAdminRunRequestModel
from api.response_models.v1.public.run_response_models import PlatformRunResponseModel


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin - Run"])


@router.get("/run/health")
async def run_health_check():
    return {
        "status": "ok",
        "run_endpoint": "/v1/admin/run",
        "method": "POST",
    }


@router.post("/run", response_model=PlatformRunResponseModel)
async def run_platform_node(request_data: PlatformAdminRunRequestModel):
    return await RunController().run(request_data)

