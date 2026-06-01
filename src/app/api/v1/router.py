"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import feed, health, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(feed.router, prefix="/users", tags=["Feed"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
