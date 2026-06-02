"""Versioned API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, devices, health, users

api_router = APIRouter(prefix="/v1")
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
