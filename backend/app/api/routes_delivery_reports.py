"""
AIuthor Backend — Evaluation, Prompt Dossier, and Delivery API Routes.

Prefix: None
Tags:   delivery-reports
"""
from __future__ import annotations

import json
import logging
from typing import Annotated, Any
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.api.error_handlers import handle_service_error
from app.workflows.schemas import (
    EvaluationReportRequest,
    EvaluationReportResponse,
    PromptDossierRequest,
    PromptDossierResponse,
    DeliveryBundleRequest,
    DeliveryBundleResponse,
)
from app.services import (
    EvaluationReportService,
    PromptDossierService,
    DeliveryBundleService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["delivery-reports"])

# ── Dependencies ──────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]

def _eval_report_service(db: DbDep) -> EvaluationReportService:
    return EvaluationReportService(db)

def _prompt_dossier_service() -> PromptDossierService:
    return PromptDossierService()

def _delivery_bundle_service(db: DbDep) -> DeliveryBundleService:
    return DeliveryBundleService(db)

EvalReportServiceDep = Annotated[EvaluationReportService, Depends(_eval_report_service)]
PromptDossierServiceDep = Annotated[PromptDossierService, Depends(_prompt_dossier_service)]
DeliveryBundleServiceDep = Annotated[DeliveryBundleService, Depends(_delivery_bundle_service)]

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/api/books/{book_id}/reports/evaluation",
    response_model=EvaluationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate evaluation report scorecard",
)
def generate_evaluation_report(
    book_id: UUID,
    payload: EvaluationReportRequest,
    svc: EvalReportServiceDep,
) -> EvaluationReportResponse:
    try:
        payload.book_id = book_id
        return svc.generate_evaluation_report(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/reports/prompt-dossier",
    response_model=PromptDossierResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate prompt dossier",
)
def generate_prompt_dossier(
    payload: PromptDossierRequest,
    svc: PromptDossierServiceDep,
) -> PromptDossierResponse:
    try:
        return svc.generate_prompt_dossier(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/books/{book_id}/delivery-bundle",
    response_model=DeliveryBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate delivery bundle files and manifest",
)
def generate_delivery_bundle(
    book_id: UUID,
    payload: DeliveryBundleRequest,
    svc: DeliveryBundleServiceDep,
) -> DeliveryBundleResponse:
    try:
        payload.book_id = book_id
        return svc.generate_delivery_bundle(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/delivery-bundle/latest",
    response_model=dict[str, Any],
    summary="Get latest generated delivery bundle manifest",
)
def get_latest_delivery_bundle(
    book_id: UUID,
) -> dict[str, Any]:
    try:
        settings = get_settings()
        book_dir = Path(settings.delivery_output_dir) / str(book_id)
        if not book_dir.exists():
            raise NotFoundError(
                message="No delivery bundle found for this book project",
                code="bundle_not_found",
                details={"book_id": str(book_id)}
            )

        manifests = []
        for p in book_dir.glob("**/manifest.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    manifests.append(data)
            except Exception:
                continue

        if not manifests:
            raise NotFoundError(
                message="No delivery bundle manifest found for this book project",
                code="manifest_not_found",
                details={"book_id": str(book_id)}
            )

        # Sort newest-first by generated_at
        manifests.sort(key=lambda m: m.get("generated_at", ""), reverse=True)
        return manifests[0]
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
