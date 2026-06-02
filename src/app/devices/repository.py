"""Repository layer for devices."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.devices.models import Device


class DeviceRepository:
    """Persist and query devices."""

    def get_by_identifier(self, session: Session, identifier: str) -> Device | None:
        """Return a device by identifier if present."""

        statement = select(Device).where(Device.identifier == identifier)
        return session.execute(statement).scalar_one_or_none()

    def create(self, session: Session, *, device: Device) -> Device:
        """Persist a new device."""

        session.add(device)
        session.flush()
        return device
