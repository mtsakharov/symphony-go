"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, retrieval, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["Retrieval"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
