from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Common parent for all Pydantic schemas.
    Configured to support ORM serialization and alias mapping.
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        protected_namespaces=(),
    )


class IDSchema(BaseSchema):
    """
    Schema helper that includes a unique identifier field.
    """
    id: UUID


class TimestampSchema(BaseSchema):
    """
    Schema helper that includes standard audit timestamp fields.
    """
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ORMBaseSchema(BaseSchema):
    """
    Common schema for ORM response objects, combining identity and timestamps.
    """
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
