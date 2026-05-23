"""
AIuthor Backend — BookSectionService.

Encapsulates all database operations for the BookSection resource.
Services are independent of FastAPI — they accept Session objects and
raise service-level exceptions, never HTTP exceptions.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.models import BookProject, BookSection
from app.schemas.section import (
    BookSectionCreate,
    BookSectionUpdate,
    REQUIRED_FRONT_MATTER_SECTIONS,
    REQUIRED_BACK_MATTER_SECTIONS,
)
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Back matter sort_order starts after a large gap so chapters fit between
_FRONT_MATTER_SORT_START = 0
_BACK_MATTER_SORT_START = 1000


class BookSectionService:
    """
    Service layer for BookSection CRUD operations.

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

    def _get_book_or_404(self, book_id: UUID) -> BookProject:
        """Fetch BookProject by id or raise NotFoundError."""
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _get_section_or_404(self, book_id: UUID, section_id: UUID) -> BookSection:
        """Fetch BookSection by id scoped to book_id or raise NotFoundError."""
        section = (
            self.db.query(BookSection)
            .filter(
                BookSection.id == section_id,
                BookSection.book_id == book_id,
            )
            .first()
        )
        if section is None:
            raise NotFoundError(
                message="Book section not found",
                code="section_not_found",
                details={"section_id": str(section_id), "book_id": str(book_id)},
            )
        return section

    # ── Public methods ────────────────────────────────────────────────────────

    def create_section(self, book_id: UUID, payload: BookSectionCreate) -> BookSection:
        """
        Create and persist a new BookSection.

        Args:
            book_id:  Path parameter — used as the source of truth.  If
                      ``payload.book_id`` differs it is silently overridden.
            payload:  Validated BookSectionCreate schema.

        Raises:
            NotFoundError: If the BookProject does not exist.

        Returns:
            The newly created BookSection ORM instance.
        """
        self._get_book_or_404(book_id)

        if payload.book_id != book_id:
            logger.warning(
                "payload.book_id=%s overridden by path book_id=%s",
                payload.book_id,
                book_id,
            )

        section = BookSection(
            book_id=book_id,
            section_type=payload.section_type,
            title=payload.title,
            content=payload.content,
            sort_order=payload.sort_order,
            status=str(payload.status) if payload.status is not None else "draft",
            section_metadata=payload.section_metadata,
        )
        self.db.add(section)
        self._commit()
        self.db.refresh(section)
        logger.info(
            "Created BookSection id=%s section_type=%s for book_id=%s",
            section.id,
            section.section_type,
            book_id,
        )
        return section

    def get_section(self, book_id: UUID, section_id: UUID) -> BookSection:
        """
        Fetch a BookSection by id, scoped to its parent BookProject.

        Raises:
            NotFoundError: If the section does not exist or belongs to a
                           different book.
        """
        return self._get_section_or_404(book_id, section_id)

    def list_sections(
        self,
        book_id: UUID,
        section_type: str | None = None,
        status: str | None = None,
    ) -> list[BookSection]:
        """
        Return all BookSections for a book, sorted by sort_order then created_at.

        Args:
            book_id:      Parent BookProject id.
            section_type: Exact match filter on section_type.
            status:       Exact match filter on status.

        Raises:
            NotFoundError: If the BookProject does not exist.

        Returns:
            List of BookSection records.
        """
        self._get_book_or_404(book_id)

        query = (
            self.db.query(BookSection)
            .filter(BookSection.book_id == book_id)
            .order_by(asc(BookSection.sort_order), asc(BookSection.created_at))
        )

        if section_type is not None:
            query = query.filter(BookSection.section_type == section_type)
        if status is not None:
            query = query.filter(BookSection.status == status)

        return query.all()

    def update_section(
        self,
        book_id: UUID,
        section_id: UUID,
        payload: BookSectionUpdate,
    ) -> BookSection:
        """
        Apply a partial update to a BookSection.

        Only fields explicitly set in *payload* (exclude_unset) are written.

        Raises:
            NotFoundError: If the section does not exist.
        """
        section = self._get_section_or_404(book_id, section_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(section, field, value)

        self._commit()
        self.db.refresh(section)
        logger.info(
            "Updated BookSection id=%s fields=%s", section_id, list(update_data)
        )
        return section

    def delete_section(self, book_id: UUID, section_id: UUID) -> bool:
        """
        Permanently delete a BookSection.

        Raises:
            NotFoundError: If the section does not exist.

        Returns:
            True on success.
        """
        section = self._get_section_or_404(book_id, section_id)
        self.db.delete(section)
        self._commit()
        logger.info("Deleted BookSection id=%s from book_id=%s", section_id, book_id)
        return True

    def create_default_structure(self, book_id: UUID) -> list[BookSection]:
        """
        Create missing required front/back matter sections for a book.

        Uses ``REQUIRED_FRONT_MATTER_SECTIONS`` and
        ``REQUIRED_BACK_MATTER_SECTIONS`` constants.  Already-existing
        section_types for this book are skipped (idempotent).

        Sort order assignment:
          - Front matter: 0, 1, 2, …
          - Back matter:  1000, 1001, 1002, …

        Raises:
            NotFoundError: If the BookProject does not exist.

        Returns:
            All sections for the book sorted by sort_order.
        """
        self._get_book_or_404(book_id)

        # Collect already-existing section_types for this book
        existing_types: set[str] = {
            row[0]
            for row in self.db.query(BookSection.section_type)
            .filter(BookSection.book_id == book_id)
            .all()
        }

        new_sections: list[BookSection] = []

        for idx, section_type in enumerate(REQUIRED_FRONT_MATTER_SECTIONS):
            if section_type in existing_types:
                continue
            new_sections.append(
                BookSection(
                    book_id=book_id,
                    section_type=section_type,
                    title=section_type.replace("_", " ").title(),
                    content=None,
                    sort_order=_FRONT_MATTER_SORT_START + idx,
                    status="draft",
                )
            )

        for idx, section_type in enumerate(REQUIRED_BACK_MATTER_SECTIONS):
            if section_type in existing_types:
                continue
            new_sections.append(
                BookSection(
                    book_id=book_id,
                    section_type=section_type,
                    title=section_type.replace("_", " ").title(),
                    content=None,
                    sort_order=_BACK_MATTER_SORT_START + idx,
                    status="draft",
                )
            )

        if new_sections:
            for s in new_sections:
                self.db.add(s)
            self._commit()
            for s in new_sections:
                self.db.refresh(s)

        logger.info(
            "Created %d default sections for book_id=%s", len(new_sections), book_id
        )

        return self.list_sections(book_id)

    def reorder_sections(self, book_id: UUID) -> list[BookSection]:
        """
        Reassign sort_order sequentially starting from 0.

        Useful after deletions or manual adjustments to close gaps.

        Raises:
            NotFoundError: If the BookProject does not exist.

        Returns:
            Updated section list sorted by the new sort_order.
        """
        self._get_book_or_404(book_id)

        sections = (
            self.db.query(BookSection)
            .filter(BookSection.book_id == book_id)
            .order_by(asc(BookSection.sort_order), asc(BookSection.created_at))
            .all()
        )
        for idx, section in enumerate(sections):
            section.sort_order = idx

        self._commit()
        for s in sections:
            self.db.refresh(s)
        logger.info(
            "Reordered %d sections for book_id=%s", len(sections), book_id
        )
        return sections
