"""Top-level API router for the agentic core."""
from fastapi import APIRouter

from api.routes.v1 import router as v1_router

router = APIRouter()
router.include_router(v1_router)

__all__ = ["router", "v1_router"]
