from api.controllers.controller_abstract import ControllerAbstract
from services.platform.admin.queries.admin_query_service import AdminQueryService
from services.platform.admin.queries.platform_config_service import PlatformConfigService
from services.platform.graph.platform_cache_manager import PlatformCacheManager


class OverviewController(ControllerAbstract):

    async def refresh_cache(self):
        await PlatformCacheManager.refresh()
        return {
            "message": "Cache refreshed successfully",
            "overview": await AdminQueryService.get_overview(),
        }

    async def overview(self):
        return await AdminQueryService.get_overview()

    async def catalog(self):
        return await AdminQueryService.get_catalog()

    async def config(self):
        return PlatformConfigService.get_default_runtime_config()

