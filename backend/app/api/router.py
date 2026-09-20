"""Versioned API root — mounted by main.py under /api/v1."""

from fastapi import APIRouter

from app.api.v1.router import router as v1_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(v1_router)
