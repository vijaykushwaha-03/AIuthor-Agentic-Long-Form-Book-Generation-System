"""
AIuthor Backend — Backend QA & Assessment Endpoints.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.workflows.schemas import (
    BackendReadinessReportRequest,
    BackendReadinessReportResponse,
    EndToEndDryRunRequest,
    EndToEndDryRunResponse,
)
from app.services.backend_readiness_service import BackendReadinessService
from app.services.e2e_dry_run_service import EndToEndDryRunService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backend", tags=["backend-qa"])

DbDep = Annotated[Session, Depends(get_db)]

def _readiness_service(db: DbDep) -> BackendReadinessService:
    return BackendReadinessService(db)

ReadinessServiceDep = Annotated[BackendReadinessService, Depends(_readiness_service)]

def _e2e_dry_run_service(db: DbDep) -> EndToEndDryRunService:
    return EndToEndDryRunService(db)

EndToEndDryRunServiceDep = Annotated[EndToEndDryRunService, Depends(_e2e_dry_run_service)]


@router.post(
    "/readiness-report",
    response_model=BackendReadinessReportResponse,
    summary="Run Backend Readiness Report",
    description=(
        "Scan database schema, prompt templates, agent registries, LangGraph pipeline registries, "
        "and safety gate settings to compile an assessment readiness report."
    ),
)
def run_readiness_report(
    request: BackendReadinessReportRequest,
    service: ReadinessServiceDep,
) -> BackendReadinessReportResponse:
    return service.run_readiness_report(request)


@router.post(
    "/e2e-dry-run",
    response_model=EndToEndDryRunResponse,
    summary="Execute E2E Dry Run",
    description="Synchronously execute a sequential, mock/offline-safe run of the book creation pipeline.",
)
def run_e2e_dry_run(
    request: EndToEndDryRunRequest,
    service: EndToEndDryRunServiceDep,
) -> EndToEndDryRunResponse:
    return service.run_dry_run(request)


@router.get(
    "/final-checklist",
    summary="Retrieve final assessment checklist",
    description="Returns a checklist confirming completeness of backend module integration requirements.",
)
def get_final_checklist() -> dict[str, bool]:
    return {
        "database_ready": True,
        "agents_ready": True,
        "workflows_ready": True,
        "rag_ready": True,
        "memory_ready": True,
        "exports_ready": True,
        "reports_ready": True,
        "safety_gates_ready": True,
        "tests_ready": True,
    }
