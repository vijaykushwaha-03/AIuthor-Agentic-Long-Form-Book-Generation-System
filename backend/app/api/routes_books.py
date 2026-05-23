"""
AIuthor Backend — BookProject API Routes.

Prefix: /api/books
Tags:   books

Endpoints:
  POST   /api/books                 — Create a new book project
  GET    /api/books                 — List book projects (paginated + filtered)
  GET    /api/books/{book_id}       — Get a single book project
  PATCH  /api/books/{book_id}       — Partially update a book project
  DELETE /api/books/{book_id}       — Delete a book project
"""
from __future__ import annotations

import math
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    BookProjectCreate,
    BookProjectUpdate,
    BookProjectResponse,
    BookProjectListItem,
    PaginatedResponse,
    MessageResponse,
)
from app.services import BookProjectService, NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books", tags=["books"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _book_service(db: DbDep) -> BookProjectService:
    return BookProjectService(db)


BookServiceDep = Annotated[BookProjectService, Depends(_book_service)]


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


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BookProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a book project",
    description="Create a new AIuthor book project from a validated brief.",
)
def create_book_project(
    payload: BookProjectCreate,
    svc: BookServiceDep,
) -> BookProjectResponse:
    try:
        book = svc.create_book_project(payload)
        return BookProjectResponse.model_validate(book)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.get(
    "",
    response_model=PaginatedResponse[BookProjectListItem],
    summary="List book projects",
    description="Return a paginated, filterable list of book projects.",
)
def list_book_projects(
    svc: BookServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    tone: str | None = Query(None, description="Filter by tone"),
    genre: str | None = Query(None, description="Filter by genre"),
    search: str | None = Query(None, description="Search topic and reader_profile"),
    sort_by: str = Query("created_at", description="Sort column"),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
) -> PaginatedResponse[BookProjectListItem]:
    items, total = svc.list_book_projects(
        page=page,
        page_size=page_size,
        status=status,
        tone=tone,
        genre=genre,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    pages = math.ceil(total / page_size) if page_size else 0
    return PaginatedResponse(
        items=[BookProjectListItem.model_validate(b) for b in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{book_id}",
    response_model=BookProjectResponse,
    summary="Get a book project",
    description="Return detailed info for a single book project by its UUID.",
)
def get_book_project(
    book_id: UUID,
    svc: BookServiceDep,
) -> BookProjectResponse:
    try:
        book = svc.get_book_project(book_id)
        return BookProjectResponse.model_validate(book)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.patch(
    "/{book_id}",
    response_model=BookProjectResponse,
    summary="Update a book project",
    description="Apply a partial update to a book project. Only provided fields are written.",
)
def update_book_project(
    book_id: UUID,
    payload: BookProjectUpdate,
    svc: BookServiceDep,
) -> BookProjectResponse:
    try:
        book = svc.update_book_project(book_id, payload)
        return BookProjectResponse.model_validate(book)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)


@router.delete(
    "/{book_id}",
    response_model=MessageResponse,
    summary="Delete a book project",
    description="Permanently delete a book project and all its associated data.",
)
def delete_book_project(
    book_id: UUID,
    svc: BookServiceDep,
) -> MessageResponse:
    try:
        svc.delete_book_project(book_id)
        return MessageResponse(message=f"Book project {book_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        _handle_service_error(exc)
