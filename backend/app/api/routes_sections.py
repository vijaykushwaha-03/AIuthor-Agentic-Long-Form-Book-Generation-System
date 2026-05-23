"""
AIuthor Backend — BookSection API Routes.

Prefix: /api/books/{book_id}/sections
Tags:   sections

Endpoints:
  POST   /api/books/{book_id}/sections                  — Create section
  GET    /api/books/{book_id}/sections                  — List sections
  POST   /api/books/{book_id}/sections/defaults         — Create default front/back matter
  POST   /api/books/{book_id}/sections/reorder          — Normalise sort_order
  GET    /api/books/{book_id}/sections/{section_id}     — Get section detail
  PATCH  /api/books/{book_id}/sections/{section_id}     — Update section
  DELETE /api/books/{book_id}/sections/{section_id}     — Delete section

NOTE: /defaults and /reorder are declared BEFORE /{section_id} so FastAPI
does not try to parse the string literals as UUIDs.
"""
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.error_handlers import handle_service_error
from app.schemas import (
    BookSectionCreate,
    BookSectionUpdate,
    BookSectionResponse,
    BookSectionListItem,
    MessageResponse,
)
from app.services import (
    BookSectionService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/books/{book_id}/sections",
    tags=["sections"],
)

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _section_service(db: DbDep) -> BookSectionService:
    return BookSectionService(db)


SectionServiceDep = Annotated[BookSectionService, Depends(_section_service)]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BookSectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a book section",
    description=(
        "Create a new front or back matter section for a book. "
        "Path book_id is the authoritative owner."
    ),
)
def create_section(
    book_id: UUID,
    payload: BookSectionCreate,
    svc: SectionServiceDep,
) -> BookSectionResponse:
    try:
        section = svc.create_section(book_id, payload)
        return BookSectionResponse.model_validate(section)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "",
    response_model=list[BookSectionListItem],
    summary="List book sections",
    description="Return all sections for a book sorted by sort_order.",
)
def list_sections(
    book_id: UUID,
    svc: SectionServiceDep,
    section_type: str | None = Query(None, description="Filter by section_type"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
) -> list[BookSectionListItem]:
    try:
        sections = svc.list_sections(
            book_id=book_id,
            section_type=section_type,
            status=status_filter,
        )
        return [BookSectionListItem.model_validate(s) for s in sections]
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/defaults",
    response_model=list[BookSectionListItem],
    status_code=status.HTTP_200_OK,
    summary="Create default front/back matter structure",
    description=(
        "Create any missing required front matter and back matter sections. "
        "Idempotent — existing section_types are not duplicated. "
        "Returns all sections for the book sorted by sort_order."
    ),
)
def create_default_structure(
    book_id: UUID,
    svc: SectionServiceDep,
) -> list[BookSectionListItem]:
    try:
        sections = svc.create_default_structure(book_id)
        return [BookSectionListItem.model_validate(s) for s in sections]
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/reorder",
    response_model=list[BookSectionListItem],
    summary="Reorder sections sequentially",
    description=(
        "Reassign sort_order sequentially starting from 0. "
        "Useful after deletions or manual adjustments."
    ),
)
def reorder_sections(
    book_id: UUID,
    svc: SectionServiceDep,
) -> list[BookSectionListItem]:
    try:
        sections = svc.reorder_sections(book_id)
        return [BookSectionListItem.model_validate(s) for s in sections]
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/{section_id}",
    response_model=BookSectionResponse,
    summary="Get a book section",
    description="Return full detail for a single book section.",
)
def get_section(
    book_id: UUID,
    section_id: UUID,
    svc: SectionServiceDep,
) -> BookSectionResponse:
    try:
        section = svc.get_section(book_id, section_id)
        return BookSectionResponse.model_validate(section)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/{section_id}",
    response_model=BookSectionResponse,
    summary="Update a book section",
    description="Apply a partial update to a section. Only provided fields are written.",
)
def update_section(
    book_id: UUID,
    section_id: UUID,
    payload: BookSectionUpdate,
    svc: SectionServiceDep,
) -> BookSectionResponse:
    try:
        section = svc.update_section(book_id, section_id, payload)
        return BookSectionResponse.model_validate(section)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/{section_id}",
    response_model=MessageResponse,
    summary="Delete a book section",
    description="Permanently delete a book section.",
)
def delete_section(
    book_id: UUID,
    section_id: UUID,
    svc: SectionServiceDep,
) -> MessageResponse:
    try:
        svc.delete_section(book_id, section_id)
        return MessageResponse(
            message=f"Book section {section_id} deleted successfully."
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
