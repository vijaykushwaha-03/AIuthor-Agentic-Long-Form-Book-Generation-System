"""
AIuthor Backend — Eval & Export API Routes.

Prefix: None (routes have varying prefixes)
Tags:   eval-export
"""
from __future__ import annotations

import math
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.error_handlers import handle_service_error
from app.schemas import (
    EvalResultCreate,
    EvalResultUpdate,
    EvalResultResponse,
    EvalReportResponse,
    ExportFileCreate,
    ExportFileUpdate,
    ExportFileResponse,
    ExportFileListItem,
    ExportBundleResponse,
    ExportRequest,
    ExportResponse,
    PaginatedResponse,
    MessageResponse,
)
from app.services import (
    EvalService,
    ExportService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["eval-export"])

# ── Dependencies ──────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _eval_service(db: DbDep) -> EvalService:
    return EvalService(db)


def _export_service(db: DbDep) -> ExportService:
    return ExportService(db)


EvalServiceDep = Annotated[EvalService, Depends(_eval_service)]
ExportServiceDep = Annotated[ExportService, Depends(_export_service)]


# ══════════════════════════════════════════════════════════════════════════════
# Eval API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/evals",
    response_model=EvalResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create evaluation result linked to book",
)
def create_eval_result(
    book_id: UUID,
    payload: EvalResultCreate,
    svc: EvalServiceDep,
) -> EvalResultResponse:
    try:
        res = svc.create_eval_result(payload, book_id=book_id)
        return EvalResultResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/evals",
    response_model=PaginatedResponse[EvalResultResponse],
    summary="List evaluation results for a book",
)
def list_eval_results(
    book_id: UUID,
    svc: EvalServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    eval_name: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    run_id: UUID | None = Query(None),
) -> PaginatedResponse[EvalResultResponse]:
    try:
        items, total = svc.list_eval_results(
            book_id=book_id,
            run_id=run_id,
            page=page,
            page_size=page_size,
            eval_name=eval_name,
            status=status_filter,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[EvalResultResponse.model_validate(r) for r in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/evals/{eval_id}",
    response_model=EvalResultResponse,
    summary="Get single evaluation result scoped to book",
)
def get_eval_result(
    book_id: UUID,
    eval_id: UUID,
    svc: EvalServiceDep,
) -> EvalResultResponse:
    try:
        res = svc.get_eval_result_for_book(book_id, eval_id)
        return EvalResultResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/evals/{eval_id}",
    response_model=EvalResultResponse,
    summary="Update evaluation result",
)
def update_eval_result(
    book_id: UUID,
    eval_id: UUID,
    payload: EvalResultUpdate,
    svc: EvalServiceDep,
) -> EvalResultResponse:
    try:
        res = svc.update_eval_result(eval_id, payload, book_id=book_id)
        return EvalResultResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/evals/{eval_id}",
    response_model=MessageResponse,
    summary="Delete evaluation result",
)
def delete_eval_result(
    book_id: UUID,
    eval_id: UUID,
    svc: EvalServiceDep,
) -> MessageResponse:
    try:
        svc.delete_eval_result(eval_id, book_id=book_id)
        return MessageResponse(message=f"Evaluation result {eval_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/eval-report",
    response_model=EvalReportResponse,
    summary="Get overall evaluation report for book project",
)
def get_eval_report(
    book_id: UUID,
    svc: EvalServiceDep,
    run_id: UUID | None = Query(None),
) -> EvalReportResponse:
    try:
        return svc.get_eval_report(book_id, run_id=run_id)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/runs/{run_id}/evals",
    response_model=EvalResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create evaluation result linked to run",
)
def create_run_eval_result(
    run_id: UUID,
    payload: EvalResultCreate,
    svc: EvalServiceDep,
) -> EvalResultResponse:
    try:
        res = svc.create_eval_result(payload, run_id=run_id)
        return EvalResultResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Export API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/exports",
    response_model=ExportFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create export file record",
)
def create_export_file(
    book_id: UUID,
    payload: ExportFileCreate,
    svc: ExportServiceDep,
) -> ExportFileResponse:
    try:
        res = svc.create_export_file(payload, book_id=book_id)
        return ExportFileResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/exports",
    response_model=PaginatedResponse[ExportFileListItem],
    summary="List export files for a book",
)
def list_export_files(
    book_id: UUID,
    svc: ExportServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    export_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    run_id: UUID | None = Query(None),
) -> PaginatedResponse[ExportFileListItem]:
    try:
        items, total = svc.list_export_files(
            book_id=book_id,
            run_id=run_id,
            page=page,
            page_size=page_size,
            export_type=export_type,
            status=status_filter,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[ExportFileListItem.model_validate(f) for f in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/books/{book_id}/exports/request",
    response_model=ExportResponse,
    summary="Create placeholder export files",
)
def request_exports(
    book_id: UUID,
    payload: ExportRequest,
    svc: ExportServiceDep,
) -> ExportResponse:
    try:
        # Override book_id in payload with path param for security/consistency
        payload.book_id = book_id
        return svc.request_exports(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/exports/bundle",
    response_model=ExportBundleResponse,
    summary="Get export files bundle report",
)
def get_export_bundle(
    book_id: UUID,
    svc: ExportServiceDep,
    run_id: UUID | None = Query(None),
) -> ExportBundleResponse:
    try:
        return svc.get_export_bundle(book_id, run_id=run_id)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/exports/{export_id}",
    response_model=ExportFileResponse,
    summary="Get single export file details",
)
def get_export_file(
    book_id: UUID,
    export_id: UUID,
    svc: ExportServiceDep,
) -> ExportFileResponse:
    try:
        res = svc.get_export_file_for_book(book_id, export_id)
        return ExportFileResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/exports/{export_id}",
    response_model=ExportFileResponse,
    summary="Update export file details",
)
def update_export_file(
    book_id: UUID,
    export_id: UUID,
    payload: ExportFileUpdate,
    svc: ExportServiceDep,
) -> ExportFileResponse:
    try:
        res = svc.update_export_file(export_id, payload, book_id=book_id)
        return ExportFileResponse.model_validate(res)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/exports/{export_id}",
    response_model=MessageResponse,
    summary="Delete export file record (DB only)",
)
def delete_export_file(
    book_id: UUID,
    export_id: UUID,
    svc: ExportServiceDep,
) -> MessageResponse:
    try:
        svc.delete_export_file(export_id, book_id=book_id)
        return MessageResponse(message=f"Export record {export_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/runs/{run_id}/exports",
    response_model=PaginatedResponse[ExportFileListItem],
    summary="List export files for a run",
)
def list_run_exports(
    run_id: UUID,
    svc: ExportServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[ExportFileListItem]:
    try:
        items, total = svc.list_export_files(
            run_id=run_id,
            page=page,
            page_size=page_size,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[ExportFileListItem.model_validate(f) for f in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
