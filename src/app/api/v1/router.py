"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, post_indexing, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(post_indexing.router, prefix="/users", tags=["Post Indexing"])
