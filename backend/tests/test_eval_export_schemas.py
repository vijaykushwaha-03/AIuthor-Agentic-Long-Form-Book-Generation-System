from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from app.schemas import (
    EvalResultCreate,
    EvalResultUpdate,
    EvalResultResponse,
    EvalMetricSummary,
    EvalReportResponse,
    ExportFileCreate,
    ExportFileUpdate,
    ExportFileResponse,
    ExportFileListItem,
    ExportBundleResponse,
    ExportRequest,
    ExportResponse,
    EvalStatus,
    ExportType,
    ExportStatus,
)


# ── 25. Package Exports Verification ──────────────────────────────────────────

def test_package_exports_eval_export():
    """Verify all evaluation and export schemas and types are properly imported from the schemas package."""
    assert EvalResultCreate is not None
    assert EvalResultUpdate is not None
    assert EvalResultResponse is not None
    assert EvalMetricSummary is not None
    assert EvalReportResponse is not None
    assert ExportFileCreate is not None
    assert ExportFileUpdate is not None
    assert ExportFileResponse is not None
    assert ExportFileListItem is not None
    assert ExportBundleResponse is not None
    assert ExportRequest is not None
    assert ExportResponse is not None


# ── EvalResult Tests ──────────────────────────────────────────────────────────

def test_eval_result_create_valid():
    """1. Valid data passes validation for EvalResultCreate."""
    book_id = uuid4()
    run_id = uuid4()
    schema = EvalResultCreate(
        run_id=run_id,
        book_id=book_id,
        eval_name="structure_eval",
        score=0.9,
        status=EvalStatus.PASSED,
        details={"avg_chapter_words": 2100}
    )
    assert schema.book_id == book_id
    assert schema.run_id == run_id
    assert schema.eval_name == "structure_eval"
    assert schema.score == 0.9
    assert schema.status == EvalStatus.PASSED


def test_eval_result_create_eval_name_too_short():
    """2. eval_name too short fails validation (min_length=2 and stripped)."""
    with pytest.raises(ValidationError):
        EvalResultCreate(
            book_id=uuid4(),
            eval_name="a",
            status="passed"
        )

    with pytest.raises(ValidationError):
        EvalResultCreate(
            book_id=uuid4(),
            eval_name="   a   ",  # strips to "a"
            status="passed"
        )


def test_eval_result_create_score_below_0():
    """3. score below 0 fails validation."""
    with pytest.raises(ValidationError):
        EvalResultCreate(
            book_id=uuid4(),
            eval_name="structure_eval",
            score=-0.1,
            status="passed"
        )


def test_eval_result_create_score_above_1():
    """4. score above 1 fails validation."""
    with pytest.raises(ValidationError):
        EvalResultCreate(
            book_id=uuid4(),
            eval_name="structure_eval",
            score=1.01,
            status="passed"
        )


def test_eval_result_create_invalid_status():
    """5. invalid status fails validation if incompatible type (like dict) is passed."""
    with pytest.raises(ValidationError):
        EvalResultCreate(
            book_id=uuid4(),
            eval_name="structure_eval",
            status={"invalid_dict": True}
        )

    # status over max length of 50 fails
    with pytest.raises(ValidationError):
        EvalResultCreate(
            book_id=uuid4(),
            eval_name="structure_eval",
            status="s" * 51
        )


def test_eval_result_update_valid():
    """6. Partial score update passes validation for EvalResultUpdate."""
    schema = EvalResultUpdate(
        score=0.85
    )
    assert schema.score == 0.85
    assert schema.eval_name is None
    assert schema.status is None


# ── EvalMetricSummary Tests ───────────────────────────────────────────────────

def test_eval_metric_summary_valid():
    """7. Valid metric passes validation for EvalMetricSummary."""
    schema = EvalMetricSummary(
        eval_name="tone_eval",
        score=0.95,
        status="passed",
        passed=True,
        failure_count=0,
        warning_count=1,
        details={"outliers": ["chapter_3"]}
    )
    assert schema.eval_name == "tone_eval"
    assert schema.score == 0.95
    assert schema.passed is True
    assert schema.failure_count == 0
    assert schema.warning_count == 1


def test_eval_metric_summary_failure_count_below_0():
    """8. failure_count below 0 fails validation."""
    with pytest.raises(ValidationError):
        EvalMetricSummary(
            eval_name="tone_eval",
            status="failed",
            failure_count=-1
        )


# ── EvalReportResponse Tests ──────────────────────────────────────────────────

def test_eval_report_response_valid():
    """9. Valid report passes validation for EvalReportResponse."""
    book_id = uuid4()
    metric = EvalMetricSummary(
        eval_name="fact_eval",
        score=1.0,
        status="passed",
        passed=True
    )
    schema = EvalReportResponse(
        book_id=book_id,
        overall_status="passed",
        overall_score=0.98,
        metrics=[metric],
        total_evals=1,
        passed_evals=1,
        failed_evals=0,
        warning_evals=0
    )
    assert schema.book_id == book_id
    assert schema.overall_score == 0.98
    assert len(schema.metrics) == 1
    assert schema.total_evals == 1


def test_eval_report_response_overall_score_above_1():
    """10. overall_score above 1 fails validation."""
    with pytest.raises(ValidationError):
        EvalReportResponse(
            book_id=uuid4(),
            overall_status="passed",
            overall_score=1.001
        )


def test_eval_report_response_total_evals_negative():
    """11. negative total_evals fails validation."""
    with pytest.raises(ValidationError):
        EvalReportResponse(
            book_id=uuid4(),
            overall_status="passed",
            total_evals=-5
        )


# ── ExportFile Tests ──────────────────────────────────────────────────────────

def test_export_file_create_docx():
    """12. Valid docx export passes validation for ExportFileCreate."""
    book_id = uuid4()
    schema = ExportFileCreate(
        book_id=book_id,
        export_type=ExportType.DOCX,
        file_path="/exports/my_book.docx",
        file_name="my_book.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        status=ExportStatus.READY,
        export_metadata={"total_pages": 45}
    )
    assert schema.book_id == book_id
    assert schema.export_type == ExportType.DOCX
    assert schema.file_path == "/exports/my_book.docx"
    assert schema.file_name == "my_book.docx"
    assert schema.status == ExportStatus.READY


def test_export_file_create_empty_file_path():
    """13. empty file_path fails validation (min_length=1 and stripped)."""
    with pytest.raises(ValidationError):
        ExportFileCreate(
            book_id=uuid4(),
            export_type="pdf",
            file_path="   ",
            file_name="book.pdf"
        )


def test_export_file_create_empty_file_name():
    """14. empty file_name fails validation (min_length=1 and stripped)."""
    with pytest.raises(ValidationError):
        ExportFileCreate(
            book_id=uuid4(),
            export_type="pdf",
            file_path="/exports/book.pdf",
            file_name="   "
        )


def test_export_file_create_mime_type_too_long():
    """15. mime_type too long (> 100) fails validation."""
    with pytest.raises(ValidationError):
        ExportFileCreate(
            book_id=uuid4(),
            export_type="pdf",
            file_path="/exports/book.pdf",
            file_name="book.pdf",
            mime_type="a" * 101
        )


def test_export_file_update_valid_partial():
    """16. Partial status update passes validation for ExportFileUpdate."""
    schema = ExportFileUpdate(
        status=ExportStatus.FAILED
    )
    assert schema.status == ExportStatus.FAILED
    assert schema.file_path is None
    assert schema.file_name is None


# ── ExportRequest Tests ───────────────────────────────────────────────────────

def test_export_request_valid():
    """17. Valid request with docx/pdf passes validation."""
    book_id = uuid4()
    schema = ExportRequest(
        book_id=book_id,
        export_types=[ExportType.DOCX, ExportType.PDF],
        include_trace_bundle=True
    )
    assert schema.book_id == book_id
    assert schema.export_types == [ExportType.DOCX, ExportType.PDF]
    assert schema.include_trace_bundle is True


def test_export_request_empty_export_types():
    """18. empty export_types fails validation."""
    with pytest.raises(ValidationError):
        ExportRequest(
            book_id=uuid4(),
            export_types=[]
        )


# ── ExportBundleResponse Tests ────────────────────────────────────────────────

def test_export_bundle_response_valid_empty():
    """19. Valid empty bundle passes validation."""
    book_id = uuid4()
    schema = ExportBundleResponse(
        book_id=book_id,
        status="success",
        total_files=0,
        ready_files=0,
        failed_files=0
    )
    assert schema.book_id == book_id
    assert schema.status == "success"
    assert schema.files == []
    assert schema.total_files == 0


def test_export_bundle_response_negative_total():
    """20. negative total_files fails validation."""
    with pytest.raises(ValidationError):
        ExportBundleResponse(
            book_id=uuid4(),
            status="success",
            total_files=-1
        )


# ── ExportResponse Tests ──────────────────────────────────────────────────────

def test_export_response_valid():
    """21. Valid response passes validation."""
    book_id = uuid4()
    schema = ExportResponse(
        book_id=book_id,
        requested_exports=["docx", "pdf"],
        created_files=[],
        status="completed"
    )
    assert schema.book_id == book_id
    assert schema.requested_exports == ["docx", "pdf"]
    assert schema.status == "completed"


def test_export_response_empty_requested_exports():
    """22. empty requested_exports fails validation."""
    with pytest.raises(ValidationError):
        ExportResponse(
            book_id=uuid4(),
            requested_exports=[],
            status="failed"
        )


# ── ORM Model Conversions Verification ─────────────────────────────────────────

def test_eval_result_response_orm():
    """23. EvalResultResponse validates from ORM-like object."""
    class MockEvalModel:
        def __init__(self):
            self.id = uuid4()
            self.run_id = uuid4()
            self.book_id = uuid4()
            self.eval_name = "tone_eval"
            self.score = 0.92
            self.status = "passed"
            self.details = {"score_breakdown": {}}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockEvalModel()
    schema = EvalResultResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.eval_name == "tone_eval"
    assert schema.score == 0.92
    assert schema.status == "passed"


def test_export_file_response_orm():
    """24. ExportFileResponse validates from ORM-like object."""
    class MockExportModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.run_id = uuid4()
            self.export_type = "pdf"
            self.file_path = "/path/to/file.pdf"
            self.file_name = "file.pdf"
            self.mime_type = "application/pdf"
            self.status = "ready"
            self.export_metadata = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockExportModel()
    schema = ExportFileResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.export_type == "pdf"
    assert schema.file_path == "/path/to/file.pdf"
    assert schema.status == "ready"
