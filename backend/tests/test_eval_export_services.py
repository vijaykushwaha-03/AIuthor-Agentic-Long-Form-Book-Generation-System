"""
AIuthor Backend Tests — Eval + Export Services unit tests.

Tests use a per-test transaction rollback for isolation against in-memory SQLite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import uuid4, UUID

from app.database import Base
import app.models  # noqa: F401

from app.services import (
    BookProjectService,
    BookRunService,
    EvalService,
    ExportService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)
from app.schemas import (
    BookProjectCreate,
    BookRunCreate,
    EvalResultCreate,
    EvalResultUpdate,
    ExportFileCreate,
    ExportFileUpdate,
    ExportRequest,
)
from app.schemas.enums import TonePreset, EvalStatus, ExportType, ExportStatus

# ── In-memory test engine ─────────────────────────────────────────────────────

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_ENGINE)
_Session = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    connection = _ENGINE.connect()
    transaction = connection.begin()
    session = _Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_book(db):
    return BookProjectService(db).create_book_project(
        BookProjectCreate(
            topic="Eval Export Test topic",
            reader_profile="Testers",
            genre="Fiction",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=3,
        )
    )


def _make_run(db, book_id):
    return BookRunService(db).create_run(
        BookRunCreate(
            book_id=book_id,
            run_metadata={"environment": "test"},
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# EvalService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEvalService:

    def test_create_eval_result_creates_eval(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = EvalService(db)

        eval_result = svc.create_eval_result(
            EvalResultCreate(
                book_id=book.id,
                run_id=run.id,
                eval_name="Readability Index",
                score=0.85,
                status=EvalStatus.PASSED,
                details={"fog_index": 8.5},
            )
        )
        assert eval_result.id is not None
        assert eval_result.book_id == book.id
        assert eval_result.run_id == run.id
        assert eval_result.eval_name == "Readability Index"
        assert eval_result.score == 0.85
        assert eval_result.status == "passed"
        assert eval_result.details == {"fog_index": 8.5}

    def test_create_eval_result_for_missing_book_raises_not_found(self, db):
        svc = EvalService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.create_eval_result(
                EvalResultCreate(
                    book_id=uuid4(),
                    eval_name="Readability Index",
                    status=EvalStatus.PASSED,
                )
            )
        assert exc.value.code == "book_not_found"

    def test_get_eval_result_returns_eval(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        created = svc.create_eval_result(
            EvalResultCreate(
                book_id=book.id,
                eval_name="Test Metric",
                status="passed",
            )
        )
        fetched = svc.get_eval_result(created.id)
        assert fetched.id == created.id
        assert fetched.eval_name == "Test Metric"

    def test_get_missing_eval_raises_not_found(self, db):
        svc = EvalService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_eval_result(uuid4())
        assert exc.value.code == "eval_not_found"

    def test_list_eval_results_filters_by_eval_name(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric A", status="passed"))
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric B", status="passed"))

        items, total = svc.list_eval_results(book_id=book.id, eval_name="Metric A")
        assert total == 1
        assert items[0].eval_name == "Metric A"

    def test_list_eval_results_filters_by_status(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric", status="passed"))
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric", status="failed"))

        items, total = svc.list_eval_results(book_id=book.id, status="failed")
        assert total == 1
        assert items[0].status == "failed"

    def test_update_eval_result_updates_score_and_status(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        created = svc.create_eval_result(
            EvalResultCreate(book_id=book.id, eval_name="Metric", status="failed", score=0.2)
        )

        updated = svc.update_eval_result(
            created.id,
            EvalResultUpdate(score=0.9, status="passed"),
            book_id=book.id,
        )
        assert updated.score == 0.9
        assert updated.status == "passed"

    def test_delete_eval_result_deletes_eval(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        created = svc.create_eval_result(
            EvalResultCreate(book_id=book.id, eval_name="Metric", status="passed")
        )

        res = svc.delete_eval_result(created.id, book_id=book.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_eval_result(created.id)

    def test_get_eval_report_empty_returns_overall_status_empty(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        report = svc.get_eval_report(book.id)
        assert report.overall_status == "empty"
        assert report.overall_score is None
        assert report.total_evals == 0
        assert len(report.metrics) == 0

    def test_get_eval_report_summarizes_passed_failed_warning_counts(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric 1", status="passed"))
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric 2", status="failed"))
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric 3", status="warning"))

        report = svc.get_eval_report(book.id)
        assert report.total_evals == 3
        assert report.passed_evals == 1
        assert report.failed_evals == 1
        assert report.warning_evals == 1
        assert report.overall_status == "failed"

    def test_get_eval_report_computes_average_overall_score(self, db):
        book = _make_book(db)
        svc = EvalService(db)
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric 1", status="passed", score=0.8))
        svc.create_eval_result(EvalResultCreate(book_id=book.id, eval_name="Metric 2", status="passed", score=0.9))

        report = svc.get_eval_report(book.id)
        assert report.overall_score == pytest.approx(0.85)
        assert report.overall_status == "passed"


# ══════════════════════════════════════════════════════════════════════════════
# ExportService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestExportService:

    def test_create_export_file_creates_export(self, db):
        book = _make_book(db)
        svc = ExportService(db)

        export_file = svc.create_export_file(
            ExportFileCreate(
                book_id=book.id,
                export_type=ExportType.DOCX,
                file_path="/exports/mybook.docx",
                file_name="mybook.docx",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                status=ExportStatus.READY,
            )
        )
        assert export_file.id is not None
        assert export_file.book_id == book.id
        assert export_file.export_type == "docx"
        assert export_file.file_path == "/exports/mybook.docx"
        assert export_file.file_name == "mybook.docx"
        assert export_file.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert export_file.status == "ready"

    def test_create_export_file_for_missing_book_raises_not_found(self, db):
        svc = ExportService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.create_export_file(
                ExportFileCreate(
                    book_id=uuid4(),
                    export_type=ExportType.PDF,
                    file_path="/exports/mybook.pdf",
                    file_name="mybook.pdf",
                )
            )
        assert exc.value.code == "book_not_found"

    def test_get_export_file_returns_export(self, db):
        book = _make_book(db)
        svc = ExportService(db)
        created = svc.create_export_file(
            ExportFileCreate(
                book_id=book.id,
                export_type=ExportType.PDF,
                file_path="/exports/mybook.pdf",
                file_name="mybook.pdf",
            )
        )
        fetched = svc.get_export_file(created.id)
        assert fetched.id == created.id
        assert fetched.export_type == "pdf"

    def test_get_missing_export_raises_not_found(self, db):
        svc = ExportService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_export_file(uuid4())
        assert exc.value.code == "export_not_found"

    def test_list_export_files_filters_by_export_type(self, db):
        book = _make_book(db)
        svc = ExportService(db)
        svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type=ExportType.PDF, file_path="p", file_name="f")
        )
        svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type=ExportType.DOCX, file_path="p", file_name="f")
        )

        items, total = svc.list_export_files(book_id=book.id, export_type=ExportType.PDF)
        assert total == 1
        assert items[0].export_type == "pdf"

    def test_list_export_files_filters_by_status(self, db):
        book = _make_book(db)
        svc = ExportService(db)
        svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type="pdf", file_path="p", file_name="f", status="created")
        )
        svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type="pdf", file_path="p", file_name="f", status="ready")
        )

        items, total = svc.list_export_files(book_id=book.id, status="ready")
        assert total == 1
        assert items[0].status == "ready"

    def test_update_export_file_updates_status(self, db):
        book = _make_book(db)
        svc = ExportService(db)
        created = svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type="pdf", file_path="p", file_name="f", status="created")
        )

        updated = svc.update_export_file(
            created.id,
            ExportFileUpdate(status=ExportStatus.READY),
            book_id=book.id,
        )
        assert updated.status == "ready"

    def test_delete_export_file_deletes_record_only(self, db):
        book = _make_book(db)
        svc = ExportService(db)
        created = svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type="pdf", file_path="p", file_name="f")
        )

        res = svc.delete_export_file(created.id, book_id=book.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_export_file(created.id)

    def test_request_exports_creates_placeholder_export_rows(self, db):
        book = _make_book(db)
        svc = ExportService(db)

        response = svc.request_exports(
            ExportRequest(
                book_id=book.id,
                export_types=[ExportType.DOCX, ExportType.PDF],
            )
        )
        assert response.status == "accepted"
        assert len(response.created_files) == 2
        assert response.created_files[0].export_type == "docx"
        assert response.created_files[1].export_type == "pdf"
        assert response.created_files[0].status == "created"
        assert response.created_files[0].export_metadata == {
            "placeholder": True,
            "real_generation": False,
            "note": "Actual file generation will be implemented later",
        }

    def test_request_exports_does_not_create_real_files_on_disk(self, db):
        book = _make_book(db)
        svc = ExportService(db)

        response = svc.request_exports(
            ExportRequest(
                book_id=book.id,
                export_types=[ExportType.DOCX],
            )
        )
        # Check database rows created
        file_record = response.created_files[0]
        # Prove the path is a virtual placeholder URI
        assert "pending://" in file_record.file_path

    def test_get_export_bundle_empty_returns_status_empty(self, db):
        book = _make_book(db)
        svc = ExportService(db)

        bundle = svc.get_export_bundle(book.id)
        assert bundle.status == "empty"
        assert bundle.total_files == 0
        assert len(bundle.files) == 0

    def test_get_export_bundle_summarizes_ready_failed_counts(self, db):
        book = _make_book(db)
        svc = ExportService(db)

        svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type="pdf", file_path="p", file_name="f", status="ready")
        )
        svc.create_export_file(
            ExportFileCreate(book_id=book.id, export_type="docx", file_path="p", file_name="f", status="failed")
        )

        bundle = svc.get_export_bundle(book.id)
        assert bundle.total_files == 2
        assert bundle.ready_files == 1
        assert bundle.failed_files == 1
        assert bundle.status == "failed"
