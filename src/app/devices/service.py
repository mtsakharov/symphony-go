"""Service layer for device registration."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import hash_secret
from app.devices.exceptions import DeviceIdentifierConflictError
from app.devices.models import Device
from app.devices.repository import DeviceRepository
from app.devices.schemas import DeviceCreate, DeviceResponse


class DeviceService:
    """Business logic for device registration."""

    def __init__(self, repository: DeviceRepository | None = None) -> None:
        self.repository = repository or DeviceRepository()

    def create_device(self, session: Session, payload: DeviceCreate) -> DeviceResponse:
        """Create a device if the identifier is unique."""

        if self.repository.get_by_identifier(session, payload.identifier) is not None:
            raise DeviceIdentifierConflictError("Device with this identifier already exists")

        device = Device(
            identifier=payload.identifier,
            secret_hash=hash_secret(payload.secret),
        )

        try:
            self.repository.create(session, device=device)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise DeviceIdentifierConflictError(
                "Device with this identifier already exists"
            ) from exc

        session.refresh(device)
        return DeviceResponse.model_validate(device)
