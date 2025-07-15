from fastapi import APIRouter
from . import auth, health, reports, utils # Add reports

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"]) # Add this line
router.include_router(utils.router, prefix="/utils", tags=["Utilities"])

__all__ = ["router"]