"""
AIuthor Backend — Workflow API Routes (Module 7.1B).

Provides endpoints to list workflows, execute mock and real traced workflows,
and retrieve complete execution trace bundles for audit logging.
"""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.workflows.schemas import (
    WorkflowInput,
    WorkflowOutput,
    WorkflowInfo,
    WorkflowTraceRequest,
    WorkflowTraceResponse,
)
from app.workflows.exceptions import WorkflowExecutionError, WorkflowError
from app.services.workflow_execution_service import WorkflowExecutionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _workflow_service(db: DbDep) -> WorkflowExecutionService:
    return WorkflowExecutionService(db)


WorkflowServiceDep = Annotated[WorkflowExecutionService, Depends(_workflow_service)]


def handle_workflow_error(exc: Exception) -> None:
    """
    Translates workflow service-layer errors to standard FastAPI HTTPExceptions.
    """
    if isinstance(exc, WorkflowExecutionError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": exc.message,
                "code": "workflow_execution_error",
                "workflow_name": exc.workflow_name,
                "details": exc.details,
            },
        )
    elif isinstance(exc, WorkflowError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": exc.message,
                "code": "workflow_error",
                "workflow_name": exc.workflow_name,
                "details": exc.details,
            },
        )
    raise exc


# ══════════════════════════════════════════════════════════════════════════════
# Workflow Endpoints (Order of declaration prevents path swallowing!)
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "",
    response_model=list[WorkflowInfo],
    summary="List all registered workflows",
    description="Return metadata for every registered LangGraph workflow, including node order and capabilities.",
)
def list_workflows(svc: WorkflowServiceDep) -> list[WorkflowInfo]:
    try:
        return svc.list_workflows()
    except Exception as exc:
        handle_workflow_error(exc)


@router.post(
    "/mock-run-traced",
    response_model=WorkflowTraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Run traced workflow in mock mode",
    description=(
        "Execute the LangGraph mini pipeline in mock mode. "
        "Persists traces, prompts, and tokens in the database if persist_traces=true. "
        "Safe for offline automated unit testing."
    ),
)
def mock_run_traced(
    payload: WorkflowTraceRequest,
    svc: WorkflowServiceDep,
) -> WorkflowTraceResponse:
    try:
        return svc.run_workflow_mock_traced(payload)
    except Exception as exc:
        handle_workflow_error(exc)


@router.post(
    "/dev-run-real-traced",
    response_model=WorkflowTraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Live traced workflow execution",
    description=(
        "Execute the LangGraph mini pipeline against live LLM providers. "
        "Persists traces, prompts, and tokens in the database if persist_traces=true. "
        "Enabled only when ENABLE_REAL_WORKFLOW_TEST_API=true. "
        "NEVER call this from automated unit tests."
    ),
)
def dev_run_real_traced(
    payload: WorkflowTraceRequest,
    svc: WorkflowServiceDep,
) -> WorkflowTraceResponse:
    settings = get_settings()
    if not settings.enable_real_workflow_test_api:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Real workflow test API is disabled. "
                "Set ENABLE_REAL_WORKFLOW_TEST_API=true for local manual testing."
            ),
        )
    try:
        return svc.run_workflow_real_dev_traced(payload)
    except Exception as exc:
        handle_workflow_error(exc)


@router.post(
    "/mock-run",
    response_model=WorkflowOutput,
    status_code=status.HTTP_200_OK,
    summary="Run workflow in mock mode (legacy)",
    description=(
        "Execute the full LangGraph pipeline using MockLLMProvider for every agent node. "
        "No external API calls are made. Safe for offline tests and API contract validation."
    ),
)
def mock_run_workflow(
    payload: WorkflowInput,
    svc: WorkflowServiceDep,
) -> WorkflowOutput:
    try:
        return svc.run_workflow_mock(payload)
    except Exception as exc:
        handle_workflow_error(exc)


@router.post(
    "/dev-run-real",
    response_model=WorkflowOutput,
    status_code=status.HTTP_200_OK,
    summary="Local dev-only real workflow execution (legacy)",
    description=(
        "Execute the full LangGraph mini_book_pipeline against configured real Gemini/OpenAI models. "
        "All 5 agent nodes (planner → researcher → writer → editor → fact_checker) are invoked in order. "
        "Enabled only when ENABLE_REAL_WORKFLOW_TEST_API=true. "
        "NEVER call this from automated tests."
    ),
)
def dev_run_real_workflow(
    payload: WorkflowInput,
    svc: WorkflowServiceDep,
) -> WorkflowOutput:
    settings = get_settings()
    if not settings.enable_real_workflow_test_api:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Real workflow test API is disabled. "
                "Set ENABLE_REAL_WORKFLOW_TEST_API=true for local manual testing."
            ),
        )
    try:
        return svc.run_workflow_real_dev(payload)
    except Exception as exc:
        handle_workflow_error(exc)


@router.get(
    "/traces/{run_id}",
    response_model=dict,
    summary="Get workflow execution trace bundle",
    description="Retrieve complete agent traces, prompt logs, and cost ledgers compiled for a specific workflow run ID.",
)
def get_workflow_trace_bundle(
    run_id: UUID,
    svc: WorkflowServiceDep,
) -> dict:
    from app.services.workflow_observability_service import WorkflowObservabilityService
    try:
        obs_svc = WorkflowObservabilityService(svc.db)
        return obs_svc.get_workflow_trace_bundle(run_id)
    except Exception as exc:
        # Check if the error is due to a missing run
        from app.services.exceptions import NotFoundError
        if isinstance(exc, NotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": exc.message,
                    "code": exc.code,
                    "details": exc.details,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to retrieve trace bundle: {exc}"},
        )


@router.get(
    "/{workflow_name}",
    response_model=WorkflowInfo,
    summary="Get workflow metadata",
    description="Fetch node list, description, and execution mode support for a specific workflow.",
)
def get_workflow_info(
    workflow_name: str,
    svc: WorkflowServiceDep,
) -> WorkflowInfo:
    try:
        return svc.get_workflow_info(workflow_name)
    except WorkflowExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": exc.message,
                "code": "workflow_not_found",
                "workflow_name": exc.workflow_name,
            },
        )
    except Exception as exc:
        handle_workflow_error(exc)
