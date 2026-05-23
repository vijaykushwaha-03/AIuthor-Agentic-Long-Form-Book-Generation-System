"""
AIuthor Backend Tests — Chapter Self-Healing API (Module 8.2).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter, AgentTrace


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
def api_test_chapters(db: Session, api_test_book: BookProject) -> list[Chapter]:
    """Fixture to provision Chapter records in db for API testing."""
    ch1 = Chapter(
        book_id=api_test_book.id,
        chapter_number=1,
        title="Scaling Microservices with RAG",
        summary="Overview of microservices",
        status="planned",
    )
    ch2 = Chapter(
        book_id=api_test_book.id,
        chapter_number=2,
        title="Advanced Distributed State",
        summary="State systems",
        status="planned",
    )
    db.add(ch1)
    db.add(ch2)
    db.commit()
    db.refresh(ch1)
    db.refresh(ch2)
    return [ch1, ch2]


class TestChapterSelfHealingAPI:

    def test_post_mock_run_returns_response(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """1. POST /api/books/{book_id}/chapters/insert-repair/mock-run returns response."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/mock-run",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Intermediary Services Patterns",
                "summary": "This middle chapter explores intermediary components.",
                "generate_content": False,
                "build_context_pack": False,
                "repair_toc": False,
                "repair_callbacks": False,
                "repair_glossary": False,
                "repair_back_matter": False,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["book_id"] == str(api_test_book.id)
        assert data["inserted_chapter_number"] == 2
        assert data["workflow_name"] == "full_agent_pipeline"
        assert data["execution_mode"] == "mock"
        assert data["status"] == "completed"

    def test_mock_run_inserts_chapter(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """2. mock-run inserts chapter."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/mock-run",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Intermediary Services Patterns",
                "generate_content": False,
                "build_context_pack": False,
                "repair_toc": False,
                "repair_callbacks": False,
                "repair_glossary": False,
                "repair_back_matter": False,
            },
        )
        assert resp.status_code == 200
        inserted_id = resp.json()["inserted_chapter_id"]
        ch = db.get(Chapter, inserted_id)
        assert ch is not None
        assert ch.title == "Intermediary Services Patterns"

    def test_mock_run_shifts_chapter_numbers(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """3. mock-run shifts chapter numbers."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/mock-run",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Inserted Chapter 2",
                "generate_content": False,
                "build_context_pack": False,
                "repair_toc": False,
                "repair_callbacks": False,
                "repair_glossary": False,
                "repair_back_matter": False,
            },
        )
        assert resp.status_code == 200

        db.refresh(api_test_chapters[0])
        db.refresh(api_test_chapters[1])

        # Verify first stays, second shifts to 3
        assert api_test_chapters[0].chapter_number == 1
        assert api_test_chapters[1].chapter_number == 3

    def test_mock_run_with_generate_content_false_works(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """4. mock-run with generate_content=false works."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/mock-run",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "No Generation Needed",
                "generate_content": False,
                "build_context_pack": False,
                "repair_toc": False,
                "repair_callbacks": False,
                "repair_glossary": False,
                "repair_back_matter": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated_content_preview"] is None

        ch = db.get(Chapter, data["inserted_chapter_id"])
        assert ch.final_text is None
        assert ch.status == "drafting"

    def test_mock_run_with_generate_content_true_persists_final_text(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """5. mock-run with generate_content=true persists final_text."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/mock-run",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Generate This Middle Segment",
                "generate_content": True,
                "build_context_pack": False,
                "traced": False,
                "repair_toc": False,
                "repair_callbacks": False,
                "repair_glossary": False,
                "repair_back_matter": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated_content_preview"] is not None

        ch = db.get(Chapter, data["inserted_chapter_id"])
        assert ch.final_text is not None
        assert "Assemble a final compact book" in ch.final_text
        assert ch.status == "completed"

    def test_invalid_book_returns_404(self, client: TestClient):
        """6. invalid book returns 404."""
        fake_id = str(uuid4())
        resp = client.post(
            f"/api/books/{fake_id}/chapters/insert-repair/mock-run",
            json={
                "book_id": fake_id,
                "insert_at_chapter_number": 1,
                "title": "Nowhere Book",
                "generate_content": False,
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "book_not_found"

    def test_dev_run_real_returns_403_by_default(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], monkeypatch):
        """7. dev-run-real returns 403 by default."""
        from app.api import routes_chapter_self_healing
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_chapter_self_healing, "get_settings", mock_get_settings)

        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/dev-run-real",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Real Gemini Attempter",
                "generate_content": True,
            },
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "real_workflow_test_api_disabled"

    def test_disabled_dev_run_real_does_not_call_gemini_openai(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], monkeypatch):
        """8. disabled dev-run-real does not call Gemini/OpenAI."""
        from app.api import routes_chapter_self_healing
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_chapter_self_healing, "get_settings", mock_get_settings)

        call_count = {"count": 0}
        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once
        def boom_run_once(self, input):
            call_count["count"] += 1
            raise RuntimeError("Real LLM called!")
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/dev-run-real",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Real Gated Run",
                "generate_content": True,
            },
        )
        assert resp.status_code == 403
        assert call_count["count"] == 0
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_get_insert_chapter_repair_run_trace_returns_bundle(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """9. GET /api/books/{book_id}/chapters/insert-repair/runs/{run_id}/trace returns trace bundle."""
        resp1 = client.post(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/mock-run",
            json={
                "book_id": str(api_test_book.id),
                "insert_at_chapter_number": 2,
                "title": "Traced API Run",
                "generate_content": True,
                "build_context_pack": False,
                "traced": True,
                "persist_traces": True,
                "repair_toc": False,
                "repair_callbacks": False,
                "repair_glossary": False,
                "repair_back_matter": False,
            },
        )
        assert resp1.status_code == 200
        run_id = resp1.json()["run_id"]

        resp2 = client.get(
            f"/api/books/{api_test_book.id}/chapters/insert-repair/runs/{run_id}/trace"
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert "traces" in data
        assert "prompt_logs" in data
        assert "token_cost_ledger" in data
        assert len(data["traces"]) == 8  # 1 chapter * 8 steps = 8 traces!

    def test_openapi_includes_insert_repair_endpoints(self, client: TestClient):
        """10. OpenAPI includes insert repair endpoints."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/books/{book_id}/chapters/insert-repair/mock-run" in paths
        assert "/api/books/{book_id}/chapters/insert-repair/dev-run-real" in paths
        assert "/api/books/{book_id}/chapters/insert-repair/runs/{run_id}/trace" in paths
