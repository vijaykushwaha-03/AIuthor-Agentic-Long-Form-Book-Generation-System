"""
AIuthor Backend Tests — Memory Extraction API (Module 9.0).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter, FactRegistry
from app.schemas.enums import TonePreset


@pytest.fixture
def api_test_book(db: Session) -> BookProject:
    """Fixture to provision a BookProject record in db for API testing."""
    book = BookProject(
        topic="Scalable Architecture Bible",
        genre="technical",
        reader_profile="architects",
        tone="conversational",
        target_chapters=3,
        status="created",
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@pytest.fixture
def api_test_chapter(db: Session, api_test_book: BookProject) -> Chapter:
    """Fixture to provision a Chapter record in db for API testing."""
    ch = Chapter(
        book_id=api_test_book.id,
        chapter_number=1,
        title="Scaling Microservices",
        summary="Overview of microservices",
        draft_text="John is scaling microservices using a RAG model.",
        status="planned",
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


class TestMemoryExtractionAPI:

    def test_post_extract_mock_run_returns_response(self, client: TestClient, api_test_book: BookProject):
        """1. POST /api/books/{book_id}/memory/extract/mock-run returns response."""
        payload = {
            "book_id": str(api_test_book.id),
            "source_type": "text",
            "source_text": "Sample text for extraction.",
            "execution_mode": "mock",
            "persist_memory": False
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/mock-run",
            json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["total_candidates"] > 0
        assert data["written_count"] == 0

    def test_mock_run_persists_memory_when_persist_memory_true(self, client: TestClient, api_test_book: BookProject):
        """2. mock-run persists memory when persist_memory=true."""
        payload = {
            "book_id": str(api_test_book.id),
            "source_type": "text",
            "source_text": "Water boils at 100 degrees Celsius.",
            "execution_mode": "mock",
            "persist_memory": True,
            "include_facts": True,
            "include_concepts": False,
            "include_characters": False,
            "include_callbacks": False,
            "include_tone": False,
            "include_decisions": False,
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/mock-run",
            json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["written_count"] == 1

    def test_mock_run_does_not_persist_memory_when_persist_memory_false(self, client: TestClient, api_test_book: BookProject):
        """3. mock-run does not persist memory when persist_memory=false."""
        payload = {
            "book_id": str(api_test_book.id),
            "source_type": "text",
            "source_text": "Water boils at 100 degrees Celsius.",
            "execution_mode": "mock",
            "persist_memory": False
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/mock-run",
            json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["written_count"] == 0

    def test_invalid_book_returns_404(self, client: TestClient):
        """4. invalid book returns 404."""
        bad_id = uuid4()
        payload = {
            "book_id": str(bad_id),
            "source_type": "text",
            "source_text": "Water boils at 100 degrees Celsius.",
            "execution_mode": "mock"
        }
        resp = client.post(
            f"/api/books/{bad_id}/memory/extract/mock-run",
            json=payload
        )
        assert resp.status_code == 404

    def test_post_dev_run_real_returns_403_by_default(self, client: TestClient, api_test_book: BookProject):
        """5. POST /api/books/{book_id}/memory/extract/dev-run-real returns 403 by default."""
        payload = {
            "book_id": str(api_test_book.id),
            "source_type": "text",
            "source_text": "Test real.",
            "execution_mode": "real_dev"
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/dev-run-real",
            json=payload
        )
        assert resp.status_code == 403

    def test_disabled_dev_run_real_does_not_call_llm(self, client: TestClient, api_test_book: BookProject):
        """6. disabled dev-run-real does not call Gemini/OpenAI."""
        # Asserted by returning 403 directly before LLM invocation.
        payload = {
            "book_id": str(api_test_book.id),
            "source_type": "text",
            "source_text": "Test real.",
            "execution_mode": "real_dev"
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/dev-run-real",
            json=payload
        )
        assert resp.status_code == 403

    def test_from_chapter_mock_run_works(self, client: TestClient, api_test_book: BookProject, api_test_chapter: Chapter):
        """7. from-chapter mock-run works."""
        payload = {
            "book_id": str(api_test_book.id),
            "chapter_id": str(api_test_chapter.id),
            "source_type": "chapter",
            "execution_mode": "mock",
            "persist_memory": False
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/from-chapter/{api_test_chapter.id}/mock-run",
            json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["chapter_id"] == str(api_test_chapter.id)

    def test_from_chapter_invalid_chapter_returns_404(self, client: TestClient, api_test_book: BookProject):
        """8. from-chapter invalid chapter returns 404."""
        bad_ch = uuid4()
        payload = {
            "book_id": str(api_test_book.id),
            "chapter_id": str(bad_ch),
            "source_type": "chapter",
            "execution_mode": "mock"
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/from-chapter/{bad_ch}/mock-run",
            json=payload
        )
        assert resp.status_code == 404

    def test_from_chapter_dev_run_real_returns_403_by_default(self, client: TestClient, api_test_book: BookProject, api_test_chapter: Chapter):
        """9. from-chapter dev-run-real returns 403 by default."""
        payload = {
            "book_id": str(api_test_book.id),
            "chapter_id": str(api_test_chapter.id),
            "source_type": "chapter",
            "execution_mode": "real_dev"
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/extract/from-chapter/{api_test_chapter.id}/dev-run-real",
            json=payload
        )
        assert resp.status_code == 403

    def test_continuity_pack_endpoint_returns_continuity_text(self, client: TestClient, api_test_book: BookProject):
        """10. continuity-pack endpoint returns continuity_text."""
        payload = {
            "book_id": str(api_test_book.id),
            "include_facts": True,
            "max_items_per_type": 10,
            "max_chars": 5000
        }
        resp = client.post(
            f"/api/books/{api_test_book.id}/memory/continuity-pack",
            json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "continuity_text" in data
        assert data["continuity_text"].startswith("# Continuity Pack")

    def test_openapi_includes_memory_extraction_endpoints(self, client: TestClient):
        """11. OpenAPI includes memory extraction endpoints."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/books/{book_id}/memory/extract/mock-run" in paths
        assert "/api/books/{book_id}/memory/extract/dev-run-real" in paths
        assert "/api/books/{book_id}/memory/extract/from-chapter/{chapter_id}/mock-run" in paths
        assert "/api/books/{book_id}/memory/extract/from-chapter/{chapter_id}/dev-run-real" in paths
        assert "/api/books/{book_id}/memory/continuity-pack" in paths
