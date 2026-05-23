"""
AIuthor Backend — Evaluation Service.

Encapsulates all database operations for evaluation results and reports.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, EvalResult
from app.schemas import (
    EvalResultCreate,
    EvalResultUpdate,
    EvalMetricSummary,
    EvalReportResponse,
)
from app.services.exceptions import NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)


class EvalService:
    """
    Service layer for evaluation operations.
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

    def _verify_book(self, book_id: UUID) -> BookProject:
        """Confirm BookProject exists, else raise NotFoundError."""
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _verify_run_optional(self, run_id: UUID | None) -> BookRun | None:
        """Confirm BookRun exists if run_id provided, else raise NotFoundError."""
        if run_id is None:
            return None
        run = self.db.get(BookRun, run_id)
        if run is None:
            raise NotFoundError(
                message="Book run not found",
                code="run_not_found",
                details={"run_id": str(run_id)},
            )
        return run

    def _enum_to_str(self, value: Any) -> str | None:
        """Convert enum values to string where needed."""
        if value is None:
            return None
        if hasattr(value, "value"):
            return value.value
        return str(value)

    def _paginate(self, query: Any, page: int, page_size: int) -> tuple[list[Any], int]:
        """Apply pagination filters and return items and total count."""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    # ── Eval Result methods ───────────────────────────────────────────────────

    def create_eval_result(
        self,
        payload: EvalResultCreate,
        book_id: UUID | None = None,
        run_id: UUID | None = None,
    ) -> EvalResult:
        """Create a new evaluation result record."""
        effective_run_id = run_id if run_id is not None else payload.run_id
        run = self._verify_run_optional(effective_run_id)

        if book_id is not None:
            effective_book_id = book_id
        elif run is not None and run.book_id is not None:
            effective_book_id = run.book_id
        else:
            effective_book_id = payload.book_id

        self._verify_book(effective_book_id)

        eval_result = EvalResult(
            book_id=effective_book_id,
            run_id=effective_run_id,
            eval_name=payload.eval_name,
            score=payload.score,
            status=self._enum_to_str(payload.status),
            details=payload.details,
        )
        self.db.add(eval_result)
        self._commit()
        self.db.refresh(eval_result)
        logger.info("Created EvalResult id=%s for book_id=%s", eval_result.id, effective_book_id)
        return eval_result

    def get_eval_result(self, eval_id: UUID) -> EvalResult:
        """Fetch an evaluation result by id."""
        res = self.db.get(EvalResult, eval_id)
        if res is None:
            raise NotFoundError(
                message="Evaluation result not found",
                code="eval_not_found",
                details={"eval_id": str(eval_id)},
            )
        return res

    def get_eval_result_for_book(self, book_id: UUID, eval_id: UUID) -> EvalResult:
        """Fetch an evaluation result scoped to a book project."""
        self._verify_book(book_id)
        res = (
            self.db.query(EvalResult)
            .filter(EvalResult.id == eval_id, EvalResult.book_id == book_id)
            .first()
        )
        if res is None:
            raise NotFoundError(
                message="Evaluation result not found for this book project",
                code="eval_not_found",
                details={"eval_id": str(eval_id), "book_id": str(book_id)},
            )
        return res

    def list_eval_results(
        self,
        book_id: UUID | None = None,
        run_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        eval_name: str | None = None,
        status: str | None = None,
    ) -> tuple[list[EvalResult], int]:
        """List paginated evaluation results sorted newest-first by created_at."""
        query = self.db.query(EvalResult)
        if book_id is not None:
            query = query.filter(EvalResult.book_id == book_id)
        if run_id is not None:
            query = query.filter(EvalResult.run_id == run_id)
        if eval_name is not None:
            query = query.filter(EvalResult.eval_name == eval_name)
        if status is not None:
            query = query.filter(EvalResult.status == self._enum_to_str(status))

        query = query.order_by(desc(EvalResult.created_at))
        return self._paginate(query, page, page_size)

    def update_eval_result(
        self,
        eval_id: UUID,
        payload: EvalResultUpdate,
        book_id: UUID | None = None,
    ) -> EvalResult:
        """Apply a partial update to an evaluation result."""
        if book_id is not None:
            res = self.get_eval_result_for_book(book_id, eval_id)
        else:
            res = self.get_eval_result(eval_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status":
                value = self._enum_to_str(value)
            setattr(res, field, value)

        self._commit()
        self.db.refresh(res)
        logger.info("Updated EvalResult id=%s", eval_id)
        return res

    def delete_eval_result(self, eval_id: UUID, book_id: UUID | None = None) -> bool:
        """Permanently delete an evaluation result record."""
        if book_id is not None:
            res = self.get_eval_result_for_book(book_id, eval_id)
        else:
            res = self.get_eval_result(eval_id)

        self.db.delete(res)
        self._commit()
        logger.info("Deleted EvalResult id=%s", eval_id)
        return True

    # ── Eval Report methods ───────────────────────────────────────────────────

    def get_eval_report(self, book_id: UUID, run_id: UUID | None = None) -> EvalReportResponse:
        """Compile and summarize evaluation results into a report."""
        self._verify_book(book_id)
        if run_id is not None:
            self._verify_run_optional(run_id)

        query = self.db.query(EvalResult).filter(EvalResult.book_id == book_id)
        if run_id is not None:
            query = query.filter(EvalResult.run_id == run_id)

        results = query.order_by(desc(EvalResult.created_at)).all()

        metrics = []
        total_evals = len(results)
        passed_evals = 0
        failed_evals = 0
        warning_evals = 0
        scores_sum = 0.0
        scores_count = 0

        for r in results:
            status = r.status
            if status == "passed":
                passed_evals += 1
            elif status == "failed":
                failed_evals += 1
            elif status == "warning":
                warning_evals += 1

            if r.score is not None:
                scores_sum += r.score
                scores_count += 1

            metrics.append(
                EvalMetricSummary(
                    eval_name=r.eval_name,
                    score=r.score,
                    status=status,
                    passed=status == "passed",
                    failure_count=1 if status == "failed" else 0,
                    warning_count=1 if status == "warning" else 0,
                    details=r.details,
                )
            )

        overall_score = (scores_sum / scores_count) if scores_count > 0 else None

        if failed_evals > 0:
            overall_status = "failed"
        elif warning_evals > 0:
            overall_status = "warning"
        elif total_evals > 0:
            overall_status = "passed"
        else:
            overall_status = "empty"

        return EvalReportResponse(
            run_id=run_id,
            book_id=book_id,
            overall_status=overall_status,
            overall_score=overall_score,
            metrics=metrics,
            total_evals=total_evals,
            passed_evals=passed_evals,
            failed_evals=failed_evals,
            warning_evals=warning_evals,
            details={
                "source": "stored_eval_results",
                "real_eval_runner": False,
            },
        )
