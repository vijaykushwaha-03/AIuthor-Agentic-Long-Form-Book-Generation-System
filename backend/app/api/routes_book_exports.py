"""
AIuthor Backend — Book Assembly & Export API Routes.

Prefix: None
Tags:   book-exports
"""
from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.error_handlers import handle_service_error
from app.workflows.schemas import (
    BookAssemblyRequest,
    BookAssemblyResponse,
    BookExportRequest,
    BookExportResponse,
)
from app.schemas.export import ExportFileResponse
from app.services import (
    BookAssemblerService,
    DocumentExportService,
    ExportService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["book-exports"])

# ── Dependencies ──────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _assembler_service(db: DbDep) -> BookAssemblerService:
    return BookAssemblerService(db)


def _document_export_service(db: DbDep) -> DocumentExportService:
    return DocumentExportService(db)


def _export_service(db: DbDep) -> ExportService:
    return ExportService(db)


AssemblerServiceDep = Annotated[BookAssemblerService, Depends(_assembler_service)]
DocumentExportServiceDep = Annotated[DocumentExportService, Depends(_document_export_service)]
ExportServiceDep = Annotated[ExportService, Depends(_export_service)]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/api/books/{book_id}/assemble",
    response_model=BookAssemblyResponse,
    status_code=status.HTTP_200_OK,
    summary="Assemble manuscript synchronously",
)
def assemble_book(
    book_id: UUID,
    payload: BookAssemblyRequest,
    svc: AssemblerServiceDep,
) -> BookAssemblyResponse:
    try:
        # Force book_id from path parameter
        payload.book_id = book_id
        return svc.assemble_book(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/books/{book_id}/exports/generate",
    response_model=BookExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Assemble and generate book export files synchronously",
)
def generate_exports(
    book_id: UUID,
    payload: BookExportRequest,
    svc: DocumentExportServiceDep,
) -> BookExportResponse:
    try:
        # Force book_id from path parameter
        payload.book_id = book_id
        return svc.export_book(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/exports/files",
    response_model=list[ExportFileResponse],
    summary="List generated export files for a book",
)
def list_exports(
    book_id: UUID,
    svc: ExportServiceDep,
) -> list[ExportFileResponse]:
    try:
        items, _ = svc.list_export_files(book_id=book_id)
        return [ExportFileResponse.model_validate(f) for f in items]
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/exports/files/{export_id}/metadata",
    response_model=dict[str, Any],
    summary="Get metadata for a specific export file",
)
def get_export_metadata(
    book_id: UUID,
    export_id: UUID,
    svc: ExportServiceDep,
) -> dict[str, Any]:
    try:
        res = svc.get_export_file_for_book(book_id, export_id)
        return res.export_metadata or {}
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
