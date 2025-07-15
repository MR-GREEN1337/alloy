from fastapi import APIRouter
from . import auth, health

router = APIRouter()

router.include_router(auth.router)
router.include_router(health.router)

__all__ = ["router"]
