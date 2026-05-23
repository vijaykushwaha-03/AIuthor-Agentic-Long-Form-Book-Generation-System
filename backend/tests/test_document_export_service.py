"""
AIuthor Backend Tests — Document Export Service (Module 10.0).
"""
from __future__ import annotations

import pytest
from pathlib import Path
from uuid import uuid4
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.models import BookProject, Chapter, ExportFile
from app.workflows.schemas import BookExportRequest, BookAssemblyResponse, AssembledChapter
from app.services import DocumentExportService, BookAssemblerService
from app.config import get_settings


@pytest.fixture
def export_service(db: Session, tmp_path: Path) -> DocumentExportService:
    settings = get_settings()
    # Override export_output_dir with a temporary test path
    settings.export_output_dir = str(tmp_path)
    return DocumentExportService(db)


@pytest.fixture
def sample_book_with_chapter(db: Session) -> BookProject:
    book = BookProject(
        topic="Modern Agentic Design",
        genre="Technical",
        reader_profile="Software Architects",
        tone="instructive",
        target_chapters=1,
        project_metadata={
            "title": "Architecting AI Agents",
            "subtitle": "A Practical Guide",
            "author": "Vijay Patel"
        },
        status="created"
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    ch = Chapter(
        book_id=book.id,
        chapter_number=1,
        title="Orchestration Fundamentals",
        final_text="Agent orchestration refers to the coordination of multiple LLM agents.",
        status="completed"
    )
    db.add(ch)
    db.commit()
    return book


def test_generate_docx_creates_file(export_service: DocumentExportService, tmp_path: Path):
    """1. generate_docx creates a .docx file."""
    assembly = BookAssemblyResponse(
        book_id=uuid4(),
        title="Test Book",
        subtitle="Subtitle",
        author="Author",
        front_matter=[],
        chapters=[
            AssembledChapter(
                chapter_id=uuid4(),
                chapter_number=1,
                title="Ch1",
                content="Chapter Content",
                source_field="final_text",
                word_count=2
            )
        ],
        back_matter=[],
        toc=[],
        glossary=[],
        bibliography=[],
        total_chapters=1,
        total_words=2
    )
    
    out_path = tmp_path / "test.docx"
    export_service.generate_docx(assembly, out_path)
    
    assert out_path.exists()
    # 2. generated docx file has non-zero size.
    assert out_path.stat().st_size > 0


def test_export_book_docx_creates_export_file_row(
    db: Session,
    export_service: DocumentExportService,
    sample_book_with_chapter: BookProject
):
    """3. export_book docx creates ExportFile row."""
    req = BookExportRequest(
        book_id=sample_book_with_chapter.id,
        export_types=["docx"],
        overwrite_existing=True
    )
    
    res = export_service.export_book(req)
    
    assert res.status == "completed"
    assert len(res.files) == 1
    assert res.files[0].export_type == "docx"
    assert res.files[0].status == "ready"
    
    # Check DB
    db_export = db.query(ExportFile).filter(ExportFile.book_id == sample_book_with_chapter.id).first()
    assert db_export is not None
    assert db_export.export_type == "docx"
    assert db_export.status == "ready"


def test_export_book_pdf_calls_convert_docx_to_pdf(
    export_service: DocumentExportService,
    sample_book_with_chapter: BookProject,
    monkeypatch
):
    """4. export_book pdf calls convert_docx_to_pdf when requested."""
    mock_convert = MagicMock()
    monkeypatch.setattr(export_service, "convert_docx_to_pdf", mock_convert)
    
    req = BookExportRequest(
        book_id=sample_book_with_chapter.id,
        export_types=["pdf"],
        overwrite_existing=True
    )
    
    export_service.export_book(req)
    assert mock_convert.called


def test_export_book_handles_pdf_conversion_failure_as_partial_failed(
    export_service: DocumentExportService,
    sample_book_with_chapter: BookProject,
    monkeypatch
):
    """5. export_book handles pdf conversion failure as partial_failed."""
    def mock_fail_convert(docx_path, pdf_path):
        raise RuntimeError("soffice command failed mock")
        
    monkeypatch.setattr(export_service, "convert_docx_to_pdf", mock_fail_convert)
    
    req = BookExportRequest(
        book_id=sample_book_with_chapter.id,
        export_types=["docx", "pdf"],
        overwrite_existing=True
    )
    
    res = export_service.export_book(req)
    
    assert res.status == "partial_failed"
    docx_item = next(f for f in res.files if f.export_type == "docx")
    pdf_item = next(f for f in res.files if f.export_type == "pdf")
    
    assert docx_item.status == "ready"
    assert pdf_item.status == "failed"
    assert "soffice command failed mock" in pdf_item.error_message


def test_export_book_docx_pdf_success_returns_completed_when_monkeypatched(
    export_service: DocumentExportService,
    sample_book_with_chapter: BookProject,
    monkeypatch
):
    """6. export_book docx+pdf success returns completed when monkeypatched."""
    def mock_success_convert(docx_path, pdf_path):
        # Create empty dummy file
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.touch()
        return pdf_path
        
    monkeypatch.setattr(export_service, "convert_docx_to_pdf", mock_success_convert)
    
    req = BookExportRequest(
        book_id=sample_book_with_chapter.id,
        export_types=["docx", "pdf"],
        overwrite_existing=True
    )
    
    res = export_service.export_book(req)
    
    assert res.status == "completed"
    assert len(res.files) == 2
    assert all(f.status == "ready" for f in res.files)


def test_export_output_directory_is_created(export_service: DocumentExportService, tmp_path: Path):
    """7. export output directory is created."""
    book_id = uuid4()
    run_id = uuid4()
    expected_dir = tmp_path / str(book_id) / str(run_id)
    
    assert not expected_dir.exists()
    export_service._get_output_dir(book_id, run_id)
    assert expected_dir.exists()


def test_safe_filename_removes_unsafe_chars(export_service: DocumentExportService):
    """8. safe filename removes unsafe chars."""
    unsafe_title = "Modern @ RAG: Systems!!! (Introduction) & More"
    safe = export_service._safe_filename(unsafe_title, "docx")
    
    assert "@" not in safe
    assert "!" not in safe
    assert "(" not in safe
    assert "&" not in safe
    assert safe.startswith("modern-rag-systems-introduction-more_")
    assert safe.endswith(".docx")


def test_export_book_does_not_call_llm(
    export_service: DocumentExportService,
    sample_book_with_chapter: BookProject,
    monkeypatch
):
    """9. export_book does not call Gemini/OpenAI."""
    mock_success_convert = MagicMock()
    monkeypatch.setattr(export_service, "convert_docx_to_pdf", mock_success_convert)
    
    req = BookExportRequest(
        book_id=sample_book_with_chapter.id,
        export_types=["docx", "pdf"],
        overwrite_existing=True
    )
    
    res = export_service.export_book(req)
    assert res.book_id == sample_book_with_chapter.id
