"""
AIuthor Backend — Export Service.

Encapsulates all database operations for generated export files and envelopes.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, ExportFile
from app.schemas import (
    ExportFileCreate,
    ExportFileUpdate,
    ExportBundleResponse,
    ExportRequest,
    ExportResponse,
    ExportFileResponse,
)
from app.services.exceptions import NotFoundError, ValidationServiceError, ConflictError

logger = logging.getLogger(__name__)


class ExportService:
    """
    Service layer for export operations.
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

    # ── Export File methods ───────────────────────────────────────────────────

    def create_export_file(
        self,
        payload: ExportFileCreate,
        book_id: UUID | None = None,
        run_id: UUID | None = None,
    ) -> ExportFile:
        """Create a new export file record."""
        effective_run_id = run_id if run_id is not None else payload.run_id
        run = self._verify_run_optional(effective_run_id)

        if book_id is not None:
            effective_book_id = book_id
        elif run is not None and run.book_id is not None:
            effective_book_id = run.book_id
        else:
            effective_book_id = payload.book_id

        self._verify_book(effective_book_id)

        export_file = ExportFile(
            book_id=effective_book_id,
            run_id=effective_run_id,
            export_type=self._enum_to_str(payload.export_type),
            file_path=payload.file_path,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            status=self._enum_to_str(payload.status),
            export_metadata=payload.export_metadata,
        )
        self.db.add(export_file)
        self._commit()
        self.db.refresh(export_file)
        logger.info("Created ExportFile id=%s for book_id=%s", export_file.id, effective_book_id)
        return export_file

    def get_export_file(self, export_id: UUID) -> ExportFile:
        """Fetch an export file by id."""
        res = self.db.get(ExportFile, export_id)
        if res is None:
            raise NotFoundError(
                message="Export file not found",
                code="export_not_found",
                details={"export_id": str(export_id)},
            )
        return res

    def get_export_file_for_book(self, book_id: UUID, export_id: UUID) -> ExportFile:
        """Fetch an export file scoped to a book project."""
        self._verify_book(book_id)
        res = (
            self.db.query(ExportFile)
            .filter(ExportFile.id == export_id, ExportFile.book_id == book_id)
            .first()
        )
        if res is None:
            raise NotFoundError(
                message="Export file not found for this book project",
                code="export_not_found",
                details={"export_id": str(export_id), "book_id": str(book_id)},
            )
        return res

    def list_export_files(
        self,
        book_id: UUID | None = None,
        run_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        export_type: str | None = None,
        status: str | None = None,
    ) -> tuple[list[ExportFile], int]:
        """List paginated export files sorted newest-first by created_at."""
        query = self.db.query(ExportFile)
        if book_id is not None:
            query = query.filter(ExportFile.book_id == book_id)
        if run_id is not None:
            query = query.filter(ExportFile.run_id == run_id)
        if export_type is not None:
            query = query.filter(ExportFile.export_type == self._enum_to_str(export_type))
        if status is not None:
            query = query.filter(ExportFile.status == self._enum_to_str(status))

        query = query.order_by(desc(ExportFile.created_at))
        return self._paginate(query, page, page_size)

    def update_export_file(
        self,
        export_id: UUID,
        payload: ExportFileUpdate,
        book_id: UUID | None = None,
    ) -> ExportFile:
        """Apply a partial update to an export file record."""
        if book_id is not None:
            res = self.get_export_file_for_book(book_id, export_id)
        else:
            res = self.get_export_file(export_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ("export_type", "status"):
                value = self._enum_to_str(value)
            setattr(res, field, value)

        self._commit()
        self.db.refresh(res)
        logger.info("Updated ExportFile id=%s", export_id)
        return res

    def delete_export_file(self, export_id: UUID, book_id: UUID | None = None) -> bool:
        """Permanently delete an export file record (DB only)."""
        if book_id is not None:
            res = self.get_export_file_for_book(book_id, export_id)
        else:
            res = self.get_export_file(export_id)

        self.db.delete(res)
        self._commit()
        logger.info("Deleted ExportFile id=%s (DB record only)", export_id)
        return True

    # ── Envelope & Request methods ────────────────────────────────────────────

    def request_exports(self, request: ExportRequest) -> ExportResponse:
        """Log placeholder export file requests for future asynchronous generation."""
        self._verify_book(request.book_id)
        self._verify_run_optional(request.run_id)

        mime_map = {
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "pdf": "application/pdf",
            "prompt_dossier": "text/markdown",
            "trace_bundle": "application/json",
            "eval_report": "application/json",
            "sample_books_zip": "application/zip",
        }

        created_files = []
        for t in request.export_types:
            export_type_str = self._enum_to_str(t)
            file_name = f"{export_type_str}_{request.book_id}.pending"
            file_path = f"pending://exports/{request.book_id}/{export_type_str}"
            mime_type = mime_map.get(export_type_str, "application/octet-stream")

            export_file = ExportFile(
                book_id=request.book_id,
                run_id=request.run_id,
                export_type=export_type_str,
                file_path=file_path,
                file_name=file_name,
                mime_type=mime_type,
                status="created",
                export_metadata={
                    "placeholder": True,
                    "real_generation": False,
                    "note": "Actual file generation will be implemented later",
                },
            )
            self.db.add(export_file)
            created_files.append(export_file)

        self._commit()

        # Refresh all created items to populate ids and timestamps
        for f in created_files:
            self.db.refresh(f)

        return ExportResponse(
            book_id=request.book_id,
            run_id=request.run_id,
            requested_exports=[self._enum_to_str(t) for t in request.export_types],
            created_files=[ExportFileResponse.model_validate(f) for f in created_files],
            status="accepted",
            message="Export request recorded. Real file generation is not implemented yet.",
        )

    def get_export_bundle(
        self,
        book_id: UUID,
        run_id: UUID | None = None,
    ) -> ExportBundleResponse:
        """Compile collections of all generated files for a run."""
        self._verify_book(book_id)
        if run_id is not None:
            self._verify_run_optional(run_id)

        query = self.db.query(ExportFile).filter(ExportFile.book_id == book_id)
        if run_id is not None:
            query = query.filter(ExportFile.run_id == run_id)

        files = query.order_by(desc(ExportFile.created_at)).all()

        total_files = len(files)
        ready_files = sum(1 for f in files if f.status == "ready")
        failed_files = sum(1 for f in files if f.status == "failed")

        if total_files == 0:
            status = "empty"
        elif failed_files > 0:
            status = "failed"
        elif ready_files == total_files:
            status = "ready"
        else:
            status = "partial"

        return ExportBundleResponse(
            book_id=book_id,
            run_id=run_id,
            files=[ExportFileResponse.model_validate(f) for f in files],
            total_files=total_files,
            ready_files=ready_files,
            failed_files=failed_files,
            status=status,
            message="Export bundle successfully compiled." if total_files > 0 else "No files generated yet.",
        )
