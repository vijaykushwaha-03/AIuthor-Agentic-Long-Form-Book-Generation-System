"""
AIuthor Backend Tests — Chapter Generation API Routes (Module 8.1).
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


class TestChapterGenerationAPI:

    def test_post_mock_run_returns_response(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """1. POST /api/books/{book_id}/chapters/generate/mock-run returns response."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["book_id"] == str(api_test_book.id)
        assert data["workflow_name"] == "full_agent_pipeline"
        assert data["completed_count"] == 2

    def test_mock_run_creates_run_if_missing(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """2. mock-run creates run if missing."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        db_run = db.get(BookRun, run_id)
        assert db_run is not None
        assert db_run.status == "completed"

    def test_mock_run_with_chapter_ids_generates_selected(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """3. mock-run with chapter_ids generates selected chapter."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "chapter_ids": [str(api_test_chapters[0].id)],
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requested"] == 1
        assert data["completed_count"] == 1
        assert data["chapters"][0]["chapter_id"] == str(api_test_chapters[0].id)

    def test_mock_run_with_chapter_numbers_generates_selected(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """4. mock-run with chapter_numbers generates selected chapter."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "chapter_numbers": [2],
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requested"] == 1
        assert data["completed_count"] == 1
        assert data["chapters"][0]["chapter_number"] == 2

    def test_mock_run_all_chapters_works(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """5. mock-run all chapters works."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requested"] == 2
        assert len(data["chapters"]) == 2

    def test_mock_run_with_traced_true_persists_traces(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], db: Session):
        """6. mock-run with traced=true persists traces."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "chapter_ids": [str(api_test_chapters[0].id)],
                "traced": True,
                "persist_traces": True,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        traces = db.query(AgentTrace).filter(AgentTrace.run_id == run_id).all()
        assert len(traces) == 8

    def test_mock_run_with_traced_false_works(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """7. mock-run with traced=false works."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["traced"] is False
        assert data["trace_bundle"] is None

    def test_mock_run_invalid_book_returns_404(self, client: TestClient):
        """8. mock-run invalid book returns 404."""
        resp = client.post(
            f"/api/books/{uuid4()}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "book_not_found"

    def test_mock_run_invalid_chapter_returns_422_or_404(self, client: TestClient, api_test_book: BookProject):
        """9. invalid chapter returns 422 or 404 depending validation design."""
        # UUID does not exist → NotFoundError (404)
        resp1 = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "chapter_ids": [str(uuid4())],
                "build_context_pack": False,
            },
        )
        assert resp1.status_code == 404
        assert resp1.json()["detail"]["code"] == "chapter_not_found"

        # Invalid chapter number → ValidationServiceError (422)
        resp2 = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "chapter_numbers": [999],
                "build_context_pack": False,
            },
        )
        assert resp2.status_code == 422
        assert resp2.json()["detail"]["code"] == "validation_error"

    def test_dev_run_real_returns_403_by_default(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], monkeypatch):
        """10. dev-run-real returns 403 by default."""
        from app.api import routes_chapter_generation
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_chapter_generation, "get_settings", mock_get_settings)

        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/dev-run-real",
            json={
                "workflow_name": "full_agent_pipeline",
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "real_workflow_test_api_disabled"

    def test_disabled_dev_run_real_does_not_call_llm(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter], monkeypatch):
        """11. disabled dev-run-real does not call Gemini/OpenAI."""
        from app.api import routes_chapter_generation
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_chapter_generation, "get_settings", mock_get_settings)

        call_count = {"count": 0}
        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once
        def boom_run_once(self, input):
            call_count["count"] += 1
            raise RuntimeError("Real LLM called!")
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        resp = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/dev-run-real",
            json={
                "workflow_name": "full_agent_pipeline",
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 403
        assert call_count["count"] == 0
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_get_chapter_generation_run_trace_returns_bundle(self, client: TestClient, api_test_book: BookProject, api_test_chapters: list[Chapter]):
        """12. GET /api/books/{book_id}/chapters/generation-runs/{run_id}/trace returns trace bundle."""
        resp1 = client.post(
            f"/api/books/{api_test_book.id}/chapters/generate/mock-run",
            json={
                "workflow_name": "full_agent_pipeline",
                "traced": True,
                "persist_traces": True,
                "build_context_pack": False,
            },
        )
        assert resp1.status_code == 200
        run_id = resp1.json()["run_id"]

        resp2 = client.get(
            f"/api/books/{api_test_book.id}/chapters/generation-runs/{run_id}/trace"
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert "traces" in data
        assert "prompt_logs" in data
        assert "token_cost_ledger" in data
        assert len(data["traces"]) == 16  # 2 chapters * 8 steps = 16 trace steps!

    def test_openapi_includes_endpoints(self, client: TestClient):
        """13. OpenAPI includes chapter generation endpoints."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/books/{book_id}/chapters/generate/mock-run" in paths
        assert "/api/books/{book_id}/chapters/generate/dev-run-real" in paths
        assert "/api/books/{book_id}/chapters/generation-runs/{run_id}/trace" in paths
