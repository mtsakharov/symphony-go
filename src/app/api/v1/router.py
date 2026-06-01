"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, users

api_router = APIRouter(prefix="/v1")
# Keep future /posts work aligned with docs/video-post-v1-decision.md.
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
