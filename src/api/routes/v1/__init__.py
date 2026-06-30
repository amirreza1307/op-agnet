from fastapi import APIRouter, Depends

from api.dependencies import require_admin_secret
from api.routes.v1.admin import router as admin_router
from api.routes.v1.public import router as public_router

router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router, dependencies=[Depends(require_admin_secret)])

__all__ = ["router", "admin_router", "public_router"]
