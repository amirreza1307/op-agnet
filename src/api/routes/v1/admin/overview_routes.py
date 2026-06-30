from fastapi import APIRouter

from api.controllers.v1.admin.overview_controller import OverviewController
from api.response_models.v1.admin.admin_response_models import (
    PlatformCacheRefreshResponseModel,
    PlatformCatalogResponseModel,
    PlatformDefaultRuntimeConfigResponseModel,
    PlatformOverviewResponseModel,
)


router = APIRouter(prefix="/v1/admin", tags=["Platform Admin"])


@router.post("/cache/refresh", response_model=PlatformCacheRefreshResponseModel)
async def refresh_platform_cache():
    return await OverviewController().refresh_cache()


@router.get("/overview", response_model=PlatformOverviewResponseModel)
async def get_overview():
    return await OverviewController().overview()


@router.get("/catalog", response_model=PlatformCatalogResponseModel)
async def get_catalog():
    return await OverviewController().catalog()


@router.get("/config", response_model=PlatformDefaultRuntimeConfigResponseModel)
async def get_platform_config():
    return await OverviewController().config()

