from fastapi import APIRouter

from api.routes.v1.admin.agent_api_key_routes import router as agent_api_key_router
from api.routes.v1.admin.channel_routes import router as channel_router
from api.routes.v1.admin.node_routes import router as node_router
from api.routes.v1.admin.overview_routes import router as overview_router
from api.routes.v1.admin.resource_routes import router as resource_router
from api.routes.v1.admin.run_routes import router as run_router
from api.routes.v1.admin.session_routes import router as session_router
from api.routes.v1.admin.tool_routes import router as tool_router

router = APIRouter()
router.include_router(agent_api_key_router)
router.include_router(channel_router)
router.include_router(overview_router)
router.include_router(run_router)
router.include_router(session_router)
router.include_router(node_router)
router.include_router(tool_router)
router.include_router(resource_router)

__all__ = ["router"]

