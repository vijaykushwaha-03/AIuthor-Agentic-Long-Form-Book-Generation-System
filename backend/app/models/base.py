"""
AIuthor Backend — Common SQLAlchemy Model Bases and Mixins.

This module defines common database utilities such as a platform-independent
GUID type (handling PostgreSQL's native UUID and SQLite's CHAR(36)),
and mixins for UUID primary keys and standard UTC timestamps.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's native UUID type, otherwise falls back to CHAR(36)
    storing as a string.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value if dialect.name == "postgresql" else str(value)
        try:
            val_uuid = uuid.UUID(value)
            return val_uuid if dialect.name == "postgresql" else str(val_uuid)
        except ValueError:
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID 'id' primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-10,  # Ensure 'id' is placed as the first column
    )


class TimestampMixin:
    """Mixin that adds 'created_at' and 'updated_at' timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

