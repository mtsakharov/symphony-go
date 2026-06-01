"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, users, video_uploads

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(video_uploads.router, prefix="/video-uploads", tags=["Video Uploads"])
