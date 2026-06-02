"""Devices database model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.users.models import utc_now


class Device(Base):
    """Database model for authenticating devices."""

    __tablename__ = "devices"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    identifier: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=func.true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
