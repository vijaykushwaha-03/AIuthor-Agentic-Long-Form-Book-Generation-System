"""
AIuthor Backend — Chapter Generation Loop API Routes (Module 8.1).
"""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.workflows.schemas import ChapterGenerationRequest, ChapterGenerationResponse
from app.services.chapter_generation_service import ChapterGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books/{book_id}/chapters", tags=["chapter-generation"])

# ── Dependencies ─────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _chapter_generation_service(db: DbDep) -> ChapterGenerationService:
    return ChapterGenerationService(db)


ServiceDep = Annotated[ChapterGenerationService, Depends(_chapter_generation_service)]

# ── Exception Helper ─────────────────────────────────────────────────────────


def handle_service_error(exc: Exception) -> None:
    """
    Translates service-layer custom exceptions into standard FastAPI HTTPExceptions.
    """
    from app.services.exceptions import NotFoundError, ValidationServiceError, ConflictError
    from app.workflows.exceptions import WorkflowConfigurationError, WorkflowExecutionError

    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": exc.message,
                "code": exc.code or "not_found",
                "details": exc.details,
            },
        )
    elif isinstance(exc, (ValidationServiceError, WorkflowConfigurationError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(exc),
                "code": "validation_error",
            },
        )
    elif isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": exc.message,
                "code": exc.code or "conflict_error",
                "details": exc.details,
            },
        )
    elif isinstance(exc, WorkflowExecutionError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": exc.message,
                "code": "workflow_execution_error",
                "workflow_name": exc.workflow_name,
                "details": exc.details,
            },
        )
    raise exc


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/generate/dev-run-real",
    response_model=ChapterGenerationResponse,
    summary="Execute chapter generation loop",
    description="Synchronously runs the chapter generation loop using live Gemini/OpenAI.",
)
def generate_chapters_real_dev(
    book_id: UUID,
    request: ChapterGenerationRequest,
    svc: ServiceDep,
) -> ChapterGenerationResponse:
    """
    Synchronous live chapter generation.
    """
    request_copy = request.model_copy(update={"book_id": book_id, "execution_mode": "real_dev"})
    try:
        return svc.generate_chapters(request_copy)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/generation-runs/{run_id}/trace",
    response_model=dict,
    summary="Get chapter generation run trace bundle",
    description="Fetches timing logs, trace steps, and token cost summaries for a chapter generation run.",
)
def get_chapter_generation_run_trace(
    book_id: UUID,
    run_id: UUID,
    svc: ServiceDep,
) -> dict:
    """
    Fetch trace logs bundle for a specific run ID scoped under book_id.
    """
    try:
        # Validate book project
        book = svc._get_book(book_id)
        # Verify run belongs to book
        svc._get_or_create_run(book, run_id=run_id)

        from app.services.workflow_observability_service import WorkflowObservabilityService
        obs_svc = WorkflowObservabilityService(svc.db)
        return obs_svc.get_workflow_trace_bundle(run_id)
    except Exception as exc:
        handle_service_error(exc)
