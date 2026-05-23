"""
AIuthor Backend — Chapter API Routes.

Prefix: /api/books/{book_id}/chapters
Tags:   chapters

Endpoints:
  POST   /api/books/{book_id}/chapters                  — Create chapter
  GET    /api/books/{book_id}/chapters                  — List chapters (paginated)
  POST   /api/books/{book_id}/chapters/insert           — Insert chapter at position
  POST   /api/books/{book_id}/chapters/reorder          — Normalise chapter numbering
  GET    /api/books/{book_id}/chapters/{chapter_id}     — Get chapter detail
  PATCH  /api/books/{book_id}/chapters/{chapter_id}     — Update chapter
  DELETE /api/books/{book_id}/chapters/{chapter_id}     — Delete chapter

NOTE: /insert and /reorder are declared BEFORE /{chapter_id} so FastAPI
does not try to parse the string literals as UUIDs.
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
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterListItem,
    ChapterInsertRequest,
    PaginatedResponse,
    MessageResponse,
)
from app.services import ChapterService, NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/books/{book_id}/chapters",
    tags=["chapters"],
)

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _chapter_service(db: DbDep) -> ChapterService:
    return ChapterService(db)


ChapterServiceDep = Annotated[ChapterService, Depends(_chapter_service)]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chapter",
    description=(
        "Create a new chapter record for a book project. "
        "Path book_id is the authoritative owner — any book_id in the request body is ignored."
    ),
)
def create_chapter(
    book_id: UUID,
    payload: ChapterCreate,
    svc: ChapterServiceDep,
) -> ChapterResponse:
    try:
        chapter = svc.create_chapter(book_id, payload)
        return ChapterResponse.model_validate(chapter)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "",
    response_model=PaginatedResponse[ChapterListItem],
    summary="List chapters",
    description="Return a paginated list of chapters for a book, sorted by chapter_number ascending.",
)
def list_chapters(
    book_id: UUID,
    svc: ChapterServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    tone: str | None = Query(None, description="Filter by tone"),
    search: str | None = Query(None, description="Search title and summary"),
) -> PaginatedResponse[ChapterListItem]:
    try:
        items, total = svc.list_chapters(
            book_id=book_id,
            page=page,
            page_size=page_size,
            status=status_filter,
            tone=tone,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[ChapterListItem.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/insert",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Insert a chapter at a position",
    description=(
        "Insert a new chapter after the specified chapter number. "
        "after_chapter=0 inserts before Chapter 1. "
        "Existing chapters are shifted up by 1. "
        "The inserted chapter is flagged with repair_required=True; "
        "real TOC/callback/glossary repair runs in a later workflow module."
    ),
)
def insert_chapter(
    book_id: UUID,
    payload: ChapterInsertRequest,
    svc: ChapterServiceDep,
) -> ChapterResponse:
    try:
        chapter = svc.insert_chapter(book_id, payload)
        return ChapterResponse.model_validate(chapter)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/reorder",
    response_model=list[ChapterListItem],
    summary="Reorder chapters sequentially",
    description=(
        "Reassign chapter_number sequentially starting from 1. "
        "Useful after deletions or manual adjustments."
    ),
)
def reorder_chapters(
    book_id: UUID,
    svc: ChapterServiceDep,
) -> list[ChapterListItem]:
    try:
        chapters = svc.reorder_chapters(book_id)
        return [ChapterListItem.model_validate(c) for c in chapters]
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Get a chapter",
    description="Return full detail for a single chapter.",
)
def get_chapter(
    book_id: UUID,
    chapter_id: UUID,
    svc: ChapterServiceDep,
) -> ChapterResponse:
    try:
        chapter = svc.get_chapter(book_id, chapter_id)
        return ChapterResponse.model_validate(chapter)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Update a chapter",
    description="Apply a partial update to a chapter. Only provided fields are written.",
)
def update_chapter(
    book_id: UUID,
    chapter_id: UUID,
    payload: ChapterUpdate,
    svc: ChapterServiceDep,
) -> ChapterResponse:
    try:
        chapter = svc.update_chapter(book_id, chapter_id, payload)
        return ChapterResponse.model_validate(chapter)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/{chapter_id}",
    response_model=MessageResponse,
    summary="Delete a chapter",
    description="Permanently delete a chapter and its associated data.",
)
def delete_chapter(
    book_id: UUID,
    chapter_id: UUID,
    svc: ChapterServiceDep,
) -> MessageResponse:
    try:
        svc.delete_chapter(book_id, chapter_id)
        return MessageResponse(
            message=f"Chapter {chapter_id} deleted successfully."
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)
