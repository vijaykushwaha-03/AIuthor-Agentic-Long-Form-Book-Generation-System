"""
AIuthor Backend — BookRun Service.

Encapsulates all database operations for the BookRun resource.
Services are independent of FastAPI — they accept Session objects and
raise service-level exceptions, never HTTP exceptions.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun
from app.schemas.run import BookRunCreate, BookRunUpdate
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class BookRunService:
    """
    Service layer for BookRun lifecycle operations.

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
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    # ── Public methods ────────────────────────────────────────────────────────

    def create_run(self, payload: BookRunCreate) -> BookRun:
        """
        Create a new BookRun for an existing BookProject.

        Raises:
            NotFoundError: If the referenced BookProject does not exist.

        Returns:
            The newly created BookRun ORM instance with status="pending".
        """
        self._get_book_or_404(payload.book_id)

        run = BookRun(
            book_id=payload.book_id,
            status="pending",
            run_metadata=payload.run_metadata,
        )
        self.db.add(run)
        self._commit()
        self.db.refresh(run)
        logger.info("Created BookRun id=%s for book_id=%s", run.id, payload.book_id)
        return run

    def get_run(self, run_id: UUID) -> BookRun:
        """
        Fetch a BookRun by primary key.

        Raises:
            NotFoundError: If no run with the given id exists.
        """
        run = self.db.get(BookRun, run_id)
        if run is None:
            raise NotFoundError(
                message="Book run not found",
                code="run_not_found",
                details={"run_id": str(run_id)},
            )
        return run

    def list_runs_for_book(
        self,
        book_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[BookRun], int]:
        """
        Return a paginated list of runs for a specific book.

        Args:
            book_id:   The parent BookProject id.
            page:      1-based page number (clamped to ≥ 1).
            page_size: Items per page (clamped to 1-100).
            status:    Optional exact match filter on ``status``.

        Raises:
            NotFoundError: If the referenced BookProject does not exist.

        Returns:
            A tuple of (items, total_count), ordered latest-first.
        """
        self._get_book_or_404(book_id)

        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = (
            self.db.query(BookRun)
            .filter(BookRun.book_id == book_id)
            .order_by(desc(BookRun.created_at))
        )

        if status is not None:
            query = query.filter(BookRun.status == status)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return items, total

    def update_run(self, run_id: UUID, payload: BookRunUpdate) -> BookRun:
        """
        Apply a partial update to a BookRun.

        Only fields explicitly set in *payload* (non-None) are written.

        Raises:
            NotFoundError: If no run with the given id exists.
        """
        run = self.get_run(run_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(run, field, value)

        self._commit()
        self.db.refresh(run)
        logger.info("Updated BookRun id=%s fields=%s", run_id, list(update_data))
        return run

    def mark_run_started(
        self, run_id: UUID, current_agent: str | None = None
    ) -> BookRun:
        """
        Transition a run to status="running".

        Sets ``started_at`` (only if not already set) and optionally
        updates ``current_agent``.

        Raises:
            NotFoundError: If no run with the given id exists.
        """
        run = self.get_run(run_id)
        run.status = "running"
        if run.started_at is None:
            run.started_at = _utcnow()
        if current_agent is not None:
            run.current_agent = current_agent
        self._commit()
        self.db.refresh(run)
        return run

    def mark_run_completed(self, run_id: UUID) -> BookRun:
        """
        Transition a run to status="completed".

        Sets ``completed_at`` and clears ``current_agent``.

        Raises:
            NotFoundError: If no run with the given id exists.
        """
        run = self.get_run(run_id)
        run.status = "completed"
        run.completed_at = _utcnow()
        run.current_agent = None
        self._commit()
        self.db.refresh(run)
        return run

    def mark_run_failed(self, run_id: UUID, error_message: str) -> BookRun:
        """
        Transition a run to status="failed".

        Sets ``completed_at`` and records the ``error_message``.

        Raises:
            NotFoundError: If no run with the given id exists.
        """
        run = self.get_run(run_id)
        run.status = "failed"
        run.completed_at = _utcnow()
        run.error_message = error_message
        self._commit()
        self.db.refresh(run)
        return run

    def update_current_agent(self, run_id: UUID, current_agent: str) -> BookRun:
        """
        Update the ``current_agent`` field of a BookRun.

        Raises:
            NotFoundError: If no run with the given id exists.
        """
        run = self.get_run(run_id)
        run.current_agent = current_agent
        self._commit()
        self.db.refresh(run)
        return run
