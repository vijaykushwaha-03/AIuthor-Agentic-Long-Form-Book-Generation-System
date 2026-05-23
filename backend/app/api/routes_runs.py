"""
AIuthor Backend — BookRun API Routes.

Prefixes:
  /api/books/{book_id}/runs  — book-scoped run management
  /api/runs/{run_id}         — run detail and lifecycle transitions

Endpoints:
  POST   /api/books/{book_id}/runs        — Create a pending run
  GET    /api/books/{book_id}/runs        — List runs for a book
  GET    /api/runs/{run_id}               — Get a run
  PATCH  /api/runs/{run_id}               — Update a run
  GET    /api/runs/{run_id}/status        — Get run status envelope
  POST   /api/runs/{run_id}/start         — Transition run → running
  POST   /api/runs/{run_id}/complete      — Transition run → completed
  POST   /api/runs/{run_id}/fail          — Transition run → failed
"""
from __future__ import annotations

import math
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BookRunCreate,
    BookRunUpdate,
    BookRunResponse,
    BookRunStatusResponse,
    PaginatedResponse,
)
from app.services import BookRunService, NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _run_service(db: DbDep) -> BookRunService:
    return BookRunService(db)


RunServiceDep = Annotated[BookRunService, Depends(_run_service)]


# ── Error mapper ──────────────────────────────────────────────────────────────

def _handle_service_error(exc: Exception) -> None:
    """Convert service exceptions into HTTP exceptions."""
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    if isinstance(exc, ValidationServiceError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    if isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"message": str(exc), "code": "internal_error"},
    )


# ── Status progress helper ────────────────────────────────────────────────────

_STATUS_PROGRESS: dict[str, float] = {
    "pending": 0.0,
    "running": 50.0,
    "completed": 100.0,
    "failed": 100.0,
    "cancelled": 100.0,
}

_STATUS_MESSAGE: dict[str, str] = {
    "pending": "Run is queued and waiting to start.",
    "running": "Run is in progress.",
    "completed": "Run completed successfully.",
    "failed": "Run failed. See error_message for details.",
    "cancelled": "Run was cancelled.",
}


# ── Book-scoped run routes ────────────────────────────────────────────────────

@router.post(
    "/api/books/{book_id}/runs",
    response_model=BookRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a run for a book",
    description="Create a new pending execution run for the specified book project.",
)
def create_run(
    book_id: UUID,
    svc: RunServiceDep,
    run_metadata: dict | None = Body(None, embed=True),
) -> BookRunResponse:
    try:
        payload = BookRunCreate(book_id=book_id, run_metadata=run_metadata)
        run = svc.create_run(payload)
        return BookRunResponse.model_validate(run)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/runs",
    response_model=PaginatedResponse[BookRunResponse],
    summary="List runs for a book",
    description="Return a paginated list of runs for the specified book project.",
)
def list_runs_for_book(
    book_id: UUID,
    svc: RunServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> PaginatedResponse[BookRunResponse]:
    try:
        items, total = svc.list_runs_for_book(
            book_id=book_id,
            page=page,
            page_size=page_size,
            status=status_filter,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[BookRunResponse.model_validate(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


# ── Run detail routes ─────────────────────────────────────────────────────────

@router.get(
    "/api/runs/{run_id}",
    response_model=BookRunResponse,
    summary="Get a run",
    description="Return detailed status and metadata for a specific run.",
)
def get_run(
    run_id: UUID,
    svc: RunServiceDep,
) -> BookRunResponse:
    try:
        run = svc.get_run(run_id)
        return BookRunResponse.model_validate(run)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.patch(
    "/api/runs/{run_id}",
    response_model=BookRunResponse,
    summary="Update a run",
    description="Apply a partial update to a run's state or metadata.",
)
def update_run(
    run_id: UUID,
    payload: BookRunUpdate,
    svc: RunServiceDep,
) -> BookRunResponse:
    try:
        run = svc.update_run(run_id, payload)
        return BookRunResponse.model_validate(run)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/status",
    response_model=BookRunStatusResponse,
    summary="Get run status",
    description=(
        "Return a monitoring-friendly status envelope for a run, "
        "including a progress percentage and human-readable message."
    ),
)
def get_run_status(
    run_id: UUID,
    svc: RunServiceDep,
) -> BookRunStatusResponse:
    try:
        run = svc.get_run(run_id)
        progress = _STATUS_PROGRESS.get(run.status, 0.0)
        message = _STATUS_MESSAGE.get(run.status, "Unknown status.")
        return BookRunStatusResponse(
            run_id=run.id,
            book_id=run.book_id,
            status=run.status,
            current_agent=run.current_agent,
            progress_percentage=progress,
            message=message,
            error_message=run.error_message,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.post(
    "/api/runs/{run_id}/start",
    response_model=BookRunResponse,
    summary="Start a run",
    description="Transition the run to status='running'. Does not trigger agent execution yet.",
)
def start_run(
    run_id: UUID,
    svc: RunServiceDep,
    current_agent: str | None = Body(None, embed=True),
) -> BookRunResponse:
    try:
        run = svc.mark_run_started(run_id, current_agent=current_agent)
        return BookRunResponse.model_validate(run)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.post(
    "/api/runs/{run_id}/complete",
    response_model=BookRunResponse,
    summary="Complete a run",
    description="Transition the run to status='completed'. For testing and manual flow only.",
)
def complete_run(
    run_id: UUID,
    svc: RunServiceDep,
) -> BookRunResponse:
    try:
        run = svc.mark_run_completed(run_id)
        return BookRunResponse.model_validate(run)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.post(
    "/api/runs/{run_id}/fail",
    response_model=BookRunResponse,
    summary="Fail a run",
    description="Transition the run to status='failed' with an error message.",
)
def fail_run(
    run_id: UUID,
    svc: RunServiceDep,
    error_message: str = Body(..., embed=True),
) -> BookRunResponse:
    try:
        run = svc.mark_run_failed(run_id, error_message=error_message)
        return BookRunResponse.model_validate(run)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)
