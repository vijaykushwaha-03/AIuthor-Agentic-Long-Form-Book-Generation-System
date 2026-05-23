"""
AIuthor Backend — ChapterService.

Encapsulates all database operations for the Chapter resource.
Services are independent of FastAPI — they accept Session objects and
raise service-level exceptions, never HTTP exceptions.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import asc, or_
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter
from app.schemas.chapter import ChapterCreate, ChapterUpdate, ChapterInsertRequest
from app.services.exceptions import NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)


class ChapterService:
    """
    Service layer for Chapter CRUD operations and insertion flow.

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

    def _get_chapter_or_404(self, book_id: UUID, chapter_id: UUID) -> Chapter:
        """Fetch Chapter by id scoped to book_id or raise NotFoundError."""
        chapter = (
            self.db.query(Chapter)
            .filter(Chapter.id == chapter_id, Chapter.book_id == book_id)
            .first()
        )
        if chapter is None:
            raise NotFoundError(
                message="Chapter not found",
                code="chapter_not_found",
                details={"chapter_id": str(chapter_id), "book_id": str(book_id)},
            )
        return chapter

    def _chapter_number_exists(self, book_id: UUID, chapter_number: int) -> bool:
        """Return True if a chapter with the given number already exists in the book."""
        return (
            self.db.query(Chapter)
            .filter(Chapter.book_id == book_id, Chapter.chapter_number == chapter_number)
            .count()
            > 0
        )

    # ── Public methods ────────────────────────────────────────────────────────

    def create_chapter(self, book_id: UUID, payload: ChapterCreate) -> Chapter:
        """
        Create and persist a new Chapter.

        Args:
            book_id:  Path parameter — used as the source of truth for book
                      ownership.  If ``payload.book_id`` differs from this it
                      is silently overridden to keep the API consistent.
            payload:  Validated ChapterCreate schema.

        Raises:
            NotFoundError:  If the BookProject does not exist.
            ConflictError:  If chapter_number already exists for this book.

        Returns:
            The newly created Chapter ORM instance.
        """
        self._get_book_or_404(book_id)

        if payload.book_id != book_id:
            logger.warning(
                "payload.book_id=%s overridden by path book_id=%s",
                payload.book_id,
                book_id,
            )

        if self._chapter_number_exists(book_id, payload.chapter_number):
            raise ConflictError(
                message=f"Chapter number {payload.chapter_number} already exists for this book",
                code="duplicate_chapter_number",
                details={
                    "book_id": str(book_id),
                    "chapter_number": payload.chapter_number,
                },
            )

        # Serialize chapter_contract if it's a Pydantic model
        contract = payload.chapter_contract
        if hasattr(contract, "model_dump"):
            contract = contract.model_dump()

        chapter = Chapter(
            book_id=book_id,
            chapter_number=payload.chapter_number,
            title=payload.title,
            summary=payload.summary,
            chapter_contract=contract,
            tone=str(payload.tone) if payload.tone is not None else None,
            status=str(payload.status) if payload.status is not None else "planned",
        )
        self.db.add(chapter)
        self._commit()
        self.db.refresh(chapter)
        logger.info(
            "Created Chapter id=%s chapter_number=%s for book_id=%s",
            chapter.id,
            chapter.chapter_number,
            book_id,
        )
        return chapter

    def get_chapter(self, book_id: UUID, chapter_id: UUID) -> Chapter:
        """
        Fetch a Chapter by id, scoped to its parent BookProject.

        Raises:
            NotFoundError: If the chapter does not exist or belongs to a
                           different book.
        """
        return self._get_chapter_or_404(book_id, chapter_id)

    def list_chapters(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        tone: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Chapter], int]:
        """
        Return a paginated, filtered list of Chapters for a book.

        Args:
            book_id:   Parent BookProject id.
            page:      1-based page number (clamped ≥ 1).
            page_size: Items per page (clamped 1-100).
            status:    Exact match filter on chapter status.
            tone:      Exact match filter on tone.
            search:    Substring search across title and summary.

        Raises:
            NotFoundError: If the BookProject does not exist.

        Returns:
            Tuple of (items sorted by chapter_number asc, total_count).
        """
        self._get_book_or_404(book_id)

        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = (
            self.db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .order_by(asc(Chapter.chapter_number))
        )

        if status is not None:
            query = query.filter(Chapter.status == status)
        if tone is not None:
            query = query.filter(Chapter.tone == tone)
        if search is not None:
            pattern = f"%{search}%"
            query = query.filter(
                or_(Chapter.title.ilike(pattern), Chapter.summary.ilike(pattern))
            )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_chapter(
        self,
        book_id: UUID,
        chapter_id: UUID,
        payload: ChapterUpdate,
    ) -> Chapter:
        """
        Apply a partial update to a Chapter.

        Only fields explicitly set in *payload* (exclude_unset) are written.

        Raises:
            NotFoundError: If the chapter does not exist.
        """
        chapter = self._get_chapter_or_404(book_id, chapter_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Serialize nested Pydantic models (e.g. ChapterContract)
            if hasattr(value, "model_dump"):
                value = value.model_dump()
            # Convert StrEnum values to plain strings
            elif hasattr(value, "value"):
                value = value.value
            setattr(chapter, field, value)

        self._commit()
        self.db.refresh(chapter)
        logger.info(
            "Updated Chapter id=%s fields=%s", chapter_id, list(update_data)
        )
        return chapter

    def delete_chapter(self, book_id: UUID, chapter_id: UUID) -> bool:
        """
        Permanently delete a Chapter.

        Raises:
            NotFoundError: If the chapter does not exist.

        Returns:
            True on success.
        """
        chapter = self._get_chapter_or_404(book_id, chapter_id)
        self.db.delete(chapter)
        self._commit()
        logger.info("Deleted Chapter id=%s from book_id=%s", chapter_id, book_id)
        return True

    def insert_chapter(
        self,
        book_id: UUID,
        payload: ChapterInsertRequest,
    ) -> Chapter:
        """
        Insert a new Chapter at the requested position by shifting existing ones.

        The new chapter is inserted **after** ``payload.after_chapter``.
        ``after_chapter=0`` inserts before Chapter 1 (i.e., new Chapter 1).

        Steps:
          1. Verify BookProject exists.
          2. Compute new_number = after_chapter + 1.
          3. Shift all chapters with chapter_number >= new_number upward by 1.
          4. Create the new Chapter with metadata flagging repair_required.
          5. Commit + refresh.

        Important:
            This method does NOT run TOC/callback/glossary repair.  The
            inserted chapter is marked with ``repair_required=True`` in its
            ``chapter_contract`` so a later workflow module can pick it up.

        Raises:
            NotFoundError: If the BookProject does not exist.
        """
        self._get_book_or_404(book_id)

        new_number: int = payload.after_chapter + 1

        # Shift all chapters at or above the insertion point (two-pass to avoid
        # transient UNIQUE constraint violations from adjacent chapter numbers).
        chapters_to_shift = (
            self.db.query(Chapter)
            .filter(
                Chapter.book_id == book_id,
                Chapter.chapter_number >= new_number,
            )
            .order_by(asc(Chapter.chapter_number))
            .all()
        )
        # Pass 1: move to large temporary values
        for idx, ch in enumerate(chapters_to_shift):
            ch.chapter_number = 10000 + idx
        self.db.flush()
        # Pass 2: assign final values (+1 each)
        for idx, ch in enumerate(chapters_to_shift):
            ch.chapter_number = (new_number + idx) + 1
        self.db.flush()

        # Build the repair-required contract metadata
        contract = {
            "inserted": True,
            "after_chapter": payload.after_chapter,
            "purpose": payload.purpose,
            "repair_required": True,
            "note": (
                "TOC/callback/glossary repair will run in later workflow module"
            ),
        }
        # Merge any extra metadata from the payload
        if payload.metadata:
            contract.update(payload.metadata)

        chapter = Chapter(
            book_id=book_id,
            chapter_number=new_number,
            title=payload.title,
            summary=payload.purpose,
            chapter_contract=contract,
            tone=str(payload.tone) if payload.tone is not None else None,
            status="planned",
        )
        self.db.add(chapter)
        self._commit()
        self.db.refresh(chapter)
        logger.info(
            "Inserted Chapter id=%s at chapter_number=%s for book_id=%s",
            chapter.id,
            new_number,
            book_id,
        )
        return chapter

    def reorder_chapters(self, book_id: UUID) -> list[Chapter]:
        """
        Reassign chapter numbers sequentially starting from 1.

        Useful after deletions or manual adjustments to close gaps.

        Raises:
            NotFoundError: If the BookProject does not exist.

        Returns:
            Updated chapter list sorted by the new chapter_number.
        """
        self._get_book_or_404(book_id)

        chapters = (
            self.db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .order_by(asc(Chapter.chapter_number))
            .all()
        )

        # Two-pass approach to avoid transient UNIQUE constraint violations.
        # Pass 1: shift all numbers to large negatives so no two rows collide.
        for idx, chapter in enumerate(chapters):
            chapter.chapter_number = -(idx + 1)
        self.db.flush()

        # Pass 2: assign the final sequential values.
        for idx, chapter in enumerate(chapters, start=1):
            chapter.chapter_number = idx

        self._commit()
        for ch in chapters:
            self.db.refresh(ch)
        logger.info(
            "Reordered %d chapters for book_id=%s", len(chapters), book_id
        )
        return chapters
