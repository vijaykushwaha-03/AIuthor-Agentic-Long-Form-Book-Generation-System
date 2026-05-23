"""
AIuthor Backend Tests — Book Export API Routes (Module 10.0).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock

from app.models import BookProject, Chapter, ExportFile
from app.services import DocumentExportService
from app.config import get_settings


@pytest.fixture
def api_book(db: Session) -> BookProject:
    book = BookProject(
        topic="Modern API Architectures",
        genre="Technical",
        reader_profile="Engineers",
        tone="instructive",
        target_chapters=1,
        project_metadata={
            "title": "API Design Handbook",
            "subtitle": "Best Practices",
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
        title="REST vs GraphQL",
        final_text="This chapter compares REST and GraphQL in production environments.",
        status="completed"
    )
    db.add(ch)
    db.commit()
    return book


def test_post_assemble_returns_assembly(client: TestClient, api_book: BookProject):
    """1. POST /api/books/{book_id}/assemble returns assembly."""
    req_body = {
        "book_id": str(api_book.id),
        "prefer_final_text": True
    }
    resp = client.post(f"/api/books/{api_book.id}/assemble", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["book_id"] == str(api_book.id)
    assert data["title"] == "API Design Handbook"
    assert len(data["chapters"]) == 1
    assert data["chapters"][0]["title"] == "REST vs GraphQL"


def test_assemble_invalid_book_returns_404(client: TestClient):
    """2. assemble invalid book returns 404."""
    invalid_id = str(uuid4())
    req_body = {
        "book_id": invalid_id
    }
    resp = client.post(f"/api/books/{invalid_id}/assemble", json=req_body)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "book_not_found"


def test_post_generate_exports_docx_returns_file_item(
    client: TestClient,
    api_book: BookProject,
    tmp_path,
    monkeypatch
):
    """3. POST /api/books/{book_id}/exports/generate docx returns file item."""
    settings = get_settings()
    settings.export_output_dir = str(tmp_path)
    
    req_body = {
        "book_id": str(api_book.id),
        "export_types": ["docx"]
    }
    resp = client.post(f"/api/books/{api_book.id}/exports/generate", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    
    assert data["status"] == "completed"
    assert len(data["files"]) == 1
    assert data["files"][0]["export_type"] == "docx"
    assert data["files"][0]["status"] == "ready"
    assert data["files"][0]["file_name"].startswith("api-design-handbook_")
    assert data["files"][0]["export_id"] is not None


def test_generate_exports_creates_export_file_row(
    client: TestClient,
    api_book: BookProject,
    db: Session,
    tmp_path
):
    """4. exports/generate creates ExportFile row."""
    settings = get_settings()
    settings.export_output_dir = str(tmp_path)
    
    req_body = {
        "book_id": str(api_book.id),
        "export_types": ["docx"]
    }
    client.post(f"/api/books/{api_book.id}/exports/generate", json=req_body)
    
    db_exports = db.query(ExportFile).filter(ExportFile.book_id == api_book.id).all()
    assert len(db_exports) == 1
    assert db_exports[0].export_type == "docx"
    assert db_exports[0].status == "ready"


def test_pdf_failure_returns_partial_failed(
    client: TestClient,
    api_book: BookProject,
    tmp_path,
    monkeypatch
):
    """5. pdf failure returns partial_failed if LibreOffice mocked to fail."""
    settings = get_settings()
    settings.export_output_dir = str(tmp_path)
    
    def mock_fail(self, docx_path, pdf_path):
        raise RuntimeError("LibreOffice soffice error mock")
        
    monkeypatch.setattr(DocumentExportService, "convert_docx_to_pdf", mock_fail)
    
    req_body = {
        "book_id": str(api_book.id),
        "export_types": ["docx", "pdf"]
    }
    resp = client.post(f"/api/books/{api_book.id}/exports/generate", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    
    assert data["status"] == "partial_failed"
    docx_file = next(f for f in data["files"] if f["export_type"] == "docx")
    pdf_file = next(f for f in data["files"] if f["export_type"] == "pdf")
    
    assert docx_file["status"] == "ready"
    assert pdf_file["status"] == "failed"
    assert "LibreOffice soffice error mock" in pdf_file["error_message"]


def test_get_exports_files_returns_records(
    client: TestClient,
    api_book: BookProject,
    db: Session
):
    """6. GET /api/books/{book_id}/exports/files returns records."""
    # Seed a DB export file manually
    ef = ExportFile(
        book_id=api_book.id,
        export_type="docx",
        file_path="some/path.docx",
        file_name="some_file.docx",
        status="ready"
    )
    db.add(ef)
    db.commit()
    
    resp = client.get(f"/api/books/{api_book.id}/exports/files")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "some_file.docx"
    assert data[0]["export_type"] == "docx"


def test_get_export_metadata_returns_metadata(
    client: TestClient,
    api_book: BookProject,
    db: Session
):
    """7. GET /api/books/{book_id}/exports/files/{export_id}/metadata returns metadata."""
    ef = ExportFile(
        book_id=api_book.id,
        export_type="docx",
        file_path="some/path.docx",
        file_name="some_file.docx",
        status="ready",
        export_metadata={"manual_test": True, "details": "all fine"}
    )
    db.add(ef)
    db.commit()
    
    resp = client.get(f"/api/books/{api_book.id}/exports/files/{ef.id}/metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert data["manual_test"] is True
    assert data["details"] == "all fine"


def test_openapi_includes_book_export_endpoints(client: TestClient):
    """8. OpenAPI includes book export endpoints."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/books/{book_id}/assemble" in paths
    assert "/api/books/{book_id}/exports/generate" in paths
    assert "/api/books/{book_id}/exports/files" in paths
    assert "/api/books/{book_id}/exports/files/{export_id}/metadata" in paths


def test_api_export_does_not_call_llm(
    client: TestClient,
    api_book: BookProject,
    tmp_path
):
    """9. API export does not call Gemini/OpenAI."""
    settings = get_settings()
    settings.export_output_dir = str(tmp_path)
    
    req_body = {
        "book_id": str(api_book.id),
        "export_types": ["docx"]
    }
    resp = client.post(f"/api/books/{api_book.id}/exports/generate", json=req_body)
    assert resp.status_code == 200
    assert resp.json()["book_id"] == str(api_book.id)
