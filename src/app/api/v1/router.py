"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import assets, health, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(assets.router, prefix="/video-assets", tags=["Assets"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
