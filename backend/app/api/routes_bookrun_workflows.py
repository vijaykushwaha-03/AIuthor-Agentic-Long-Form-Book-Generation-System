"""
AIuthor Backend — BookRun Workflow API Routes (Module 8.0).

Exposes BookProject-backed multi-agent workflow execution endpoints, allowing
real book project configurations to trigger LangGraph sequential execution runs.
"""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.workflows.schemas import BookRunWorkflowRequest, BookRunWorkflowResponse
from app.services.bookrun_workflow_service import BookRunWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books/{book_id}/workflow", tags=["book-run-workflows"])

# ── Dependencies ─────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _bookrun_workflow_service(db: DbDep) -> BookRunWorkflowService:
    return BookRunWorkflowService(db)


ServiceDep = Annotated[BookRunWorkflowService, Depends(_bookrun_workflow_service)]

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
    "/mock-run",
    response_model=BookRunWorkflowResponse,
    summary="Execute BookProject workflow in Mock mode",
    description="Synchronously runs the sequential multi-agent LangGraph workflow using MockLLMProvider.",
)
def run_book_workflow_mock(
    book_id: UUID,
    request: BookRunWorkflowRequest,
    svc: ServiceDep,
) -> BookRunWorkflowResponse:
    """
    Triggers synchronous offline mock multi-agent execution, securing path book_id parameters.
    """
    # Enforce mock execution mode regardless of request payload
    request_copy = request.model_copy(update={"book_id": book_id, "execution_mode": "mock"})
    try:
        return svc.run_book_workflow(request_copy)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/dev-run-real",
    response_model=BookRunWorkflowResponse,
    summary="Execute BookProject workflow in Real mode (Gated)",
    description="Synchronously runs the multi-agent LangGraph workflow using live Gemini/OpenAI APIs.",
)
def run_book_workflow_real_dev(
    book_id: UUID,
    request: BookRunWorkflowRequest,
    svc: ServiceDep,
) -> BookRunWorkflowResponse:
    """
    Triggers live multi-agent execution. Gated by ENABLE_REAL_WORKFLOW_TEST_API.
    """
    settings = get_settings()
    if not settings.enable_real_workflow_test_api:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Real workflow execution API is disabled in this environment.",
                "code": "real_workflow_test_api_disabled",
            },
        )

    # Force execution mode = real_dev
    request_copy = request.model_copy(update={"book_id": book_id, "execution_mode": "real_dev"})
    try:
        return svc.run_book_workflow(request_copy)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/runs/{run_id}/trace",
    response_model=dict,
    summary="Get run trace bundle for book workflow",
    description="Compiles and returns the deep execution trace bundle (traces, prompts, token cost logs) for a specific BookRun.",
)
def get_book_workflow_run_trace(
    book_id: UUID,
    run_id: UUID,
    svc: ServiceDep,
) -> dict:
    """
    Fetch complete trace logs bundle for a specific run ID scoped under book_id.
    """
    try:
        # First validate the book and run exist and run belongs to book
        book = svc._get_book(book_id)
        # Verify run belongs to book
        svc._get_or_create_run(book, run_id=run_id)

        from app.services.workflow_observability_service import WorkflowObservabilityService
        obs_svc = WorkflowObservabilityService(svc.db)
        return obs_svc.get_workflow_trace_bundle(run_id)
    except Exception as exc:
        handle_service_error(exc)
