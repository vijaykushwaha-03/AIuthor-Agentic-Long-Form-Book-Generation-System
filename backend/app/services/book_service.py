"""
AIuthor Backend — BookProject Service.

Encapsulates all database operations for the BookProject resource.
Services are independent of FastAPI — they accept Session objects and
raise service-level exceptions, never HTTP exceptions.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models import BookProject
from app.schemas.book import BookProjectCreate, BookProjectUpdate
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Columns that are valid for sorting
_SORTABLE_FIELDS: dict[str, Any] = {
    "created_at": BookProject.created_at,
    "updated_at": BookProject.updated_at,
    "topic": BookProject.topic,
    "status": BookProject.status,
}


class BookProjectService:
    """
    Service layer for BookProject CRUD operations.

    All write operations commit + refresh within _commit(); any DB error
    causes a rollback before re-raising.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit(self) -> None:
        """Commit the current transaction; rollback and re-raise on failure."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ── Public methods ────────────────────────────────────────────────────────

    def create_book_project(self, payload: BookProjectCreate) -> BookProject:
        """
        Create and persist a new BookProject from validated payload data.

        Returns:
            The newly created BookProject ORM instance.
        """
        book = BookProject(
            topic=payload.topic,
            reader_profile=payload.reader_profile,
            genre=payload.genre,
            tone=str(payload.tone),
            target_chapters=payload.target_chapters,
            words_per_chapter=payload.words_per_chapter,
            project_metadata=payload.project_metadata,
            status="created",
        )
        self.db.add(book)
        self._commit()
        self.db.refresh(book)
        logger.info("Created BookProject id=%s", book.id)
        return book

    def get_book_project(self, book_id: UUID) -> BookProject:
        """
        Fetch a BookProject by primary key.

        Raises:
            NotFoundError: If no project with the given id exists.
        """
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def list_book_projects(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        tone: str | None = None,
        genre: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[BookProject], int]:
        """
        Return a paginated, filtered list of BookProject records.

        Args:
            page:       1-based page number (clamped to ≥ 1).
            page_size:  Items per page (clamped to 1-100).
            status:     Exact match filter on the ``status`` column.
            tone:       Exact match filter on the ``tone`` column.
            genre:      Case-insensitive match filter on the ``genre`` column.
            search:     Substring search across ``topic`` and ``reader_profile``.
            sort_by:    Column name to order by; falls back to ``created_at``.
            sort_order: "asc" or "desc" (default "desc").

        Returns:
            A tuple of (items, total_count).
        """
        # Clamp pagination
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(BookProject)

        # Filters
        if status is not None:
            query = query.filter(BookProject.status == status)
        if tone is not None:
            query = query.filter(BookProject.tone == tone)
        if genre is not None:
            query = query.filter(BookProject.genre.ilike(f"%{genre}%"))
        if search is not None:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    BookProject.topic.ilike(pattern),
                    BookProject.reader_profile.ilike(pattern),
                )
            )

        # Sorting — unknown columns fall back to created_at
        sort_col = _SORTABLE_FIELDS.get(sort_by, BookProject.created_at)
        direction = asc if sort_order == "asc" else desc
        query = query.order_by(direction(sort_col))

        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return items, total

    def update_book_project(
        self, book_id: UUID, payload: BookProjectUpdate
    ) -> BookProject:
        """
        Apply a partial update to a BookProject.

        Only fields explicitly set in *payload* (non-None) are written.

        Raises:
            NotFoundError: If no project with the given id exists.
        """
        book = self.get_book_project(book_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Convert StrEnum values to plain strings
            if hasattr(value, "value"):
                value = value.value
            setattr(book, field, value)

        self._commit()
        self.db.refresh(book)
        logger.info("Updated BookProject id=%s fields=%s", book_id, list(update_data))
        return book

    def delete_book_project(self, book_id: UUID) -> bool:
        """
        Permanently delete a BookProject (cascade deletes all related records).

        Raises:
            NotFoundError: If no project with the given id exists.

        Returns:
            True on success.
        """
        book = self.get_book_project(book_id)
        self.db.delete(book)
        self._commit()
        logger.info("Deleted BookProject id=%s", book_id)
        return True

    def mark_status(self, book_id: UUID, status: str) -> BookProject:
        """
        Update the status field of a BookProject.

        Raises:
            NotFoundError: If no project with the given id exists.
        """
        book = self.get_book_project(book_id)
        book.status = status
        self._commit()
        self.db.refresh(book)
        return book
