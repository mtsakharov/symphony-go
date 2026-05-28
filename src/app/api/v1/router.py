"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, permissions, roles, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
