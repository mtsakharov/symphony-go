"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import feed, health, posts, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(feed.router, tags=["Feed"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(posts.router, prefix="/posts", tags=["Posts"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
