"""v1 router — all versioned endpoints aggregate here."""

from fastapi import APIRouter

from app.api.v1.conversions import router as conversions_router
from app.api.v1.health import router as health_router

router = APIRouter()
router.include_router(health_router)
router.include_router(conversions_router)
