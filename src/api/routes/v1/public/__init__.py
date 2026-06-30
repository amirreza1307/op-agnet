from fastapi import APIRouter

from api.routes.v1.public.agent_routes import router as agent_router
from api.routes.v1.public.channel_routes import router as channel_router

router = APIRouter()
router.include_router(agent_router)
router.include_router(channel_router)

__all__ = ["router"]
