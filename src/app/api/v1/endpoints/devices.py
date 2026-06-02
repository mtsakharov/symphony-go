"""Device registration endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.devices.exceptions import DeviceIdentifierConflictError
from app.devices.schemas import DeviceCreate, DeviceResponse
from app.devices.service import DeviceService

router = APIRouter()


def get_device_service() -> DeviceService:
    """Return a devices service instance."""

    return DeviceService()


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register device",
    description="Register a device identifier and shared secret for later JWT authentication.",
    operation_id="createDevice",
)
def create_device(
    payload: DeviceCreate,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> DeviceResponse:
    """Register a device."""

    try:
        return service.create_device(session, payload)
    except DeviceIdentifierConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
