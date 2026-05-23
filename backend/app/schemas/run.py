from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import Field
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import RunStatus, AgentName


class BookRunCreate(BaseSchema):
    """
    Schema for validating requests to create a new run for a project.
    """
    book_id: UUID
    run_metadata: dict | None = None


class BookRunStartRequest(BaseSchema):
    """
    Schema for validating the execution parameters on run startup.
    """
    run_metadata: dict | None = None


class BookRunUpdate(BaseSchema):
    """
    Schema for validating state transitions and logs during execution.
    """
    status: RunStatus | None = None
    current_agent: AgentName | str | None = None
    error_message: str | None = Field(None, max_length=5000)
    run_metadata: dict | None = None


class BookRunResponse(ORMBaseSchema):
    """
    Response schema returning detailed status and metrics for a book run.
    """
    book_id: UUID
    status: str
    current_agent: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    run_metadata: dict | None


class BookRunStatusResponse(BaseSchema):
    """
    Real-time status monitor schema for tracking ongoing run progress.
    """
    run_id: UUID
    book_id: UUID
    status: str
    current_agent: str | None
    progress_percentage: float | None = Field(None, ge=0.0, le=100.0)
    message: str | None = None
    error_message: str | None = None
