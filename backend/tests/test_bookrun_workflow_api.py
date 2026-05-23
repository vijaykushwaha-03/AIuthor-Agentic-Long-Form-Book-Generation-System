"""
AIuthor Backend Tests — BookRun Workflow API Routes (Module 8.0).
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
        topic="Cloud native systems",
        genre="technical",
        reader_profile="developers",
        tone="precise",
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
    chapter = Chapter(
        book_id=api_test_book.id,
        chapter_number=1,
        title="Scaling Microservices",
        summary="Scaling concepts",
        status="planned",
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


class TestBookRunWorkflowAPI:

    def test_mock_run_returns_response(self, client: TestClient, api_test_book: BookProject):
        """1. POST /api/books/{book_id}/workflow/mock-run returns response."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["book_id"] == str(api_test_book.id)
        assert data["workflow_name"] == "mini_book_pipeline"
        assert data["status"] == "completed"

    def test_mock_run_creates_run_if_missing(self, client: TestClient, api_test_book: BookProject, db: Session):
        """2. mock-run creates run if missing."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        db_run = db.get(BookRun, run_id)
        assert db_run is not None
        assert db_run.status == "completed"

    def test_mock_run_with_traced_true_persists_traces(self, client: TestClient, api_test_book: BookProject, db: Session):
        """3. mock-run with traced=true persists traces."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "traced": True,
                "persist_traces": True,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        traces = db.query(AgentTrace).filter(AgentTrace.run_id == run_id).all()
        assert len(traces) == 5

    def test_mock_run_with_traced_false_works(self, client: TestClient, api_test_book: BookProject, db: Session):
        """4. mock-run with traced=false still works."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "traced": False,
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["traced"] is False
        assert data["trace_bundle"] is None

    def test_mock_run_invalid_book_returns_404(self, client: TestClient):
        """5. mock-run invalid book returns 404."""
        resp = client.post(
            f"/api/books/{uuid4()}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "book_not_found"

    def test_mock_run_invalid_chapter_returns_404(self, client: TestClient, api_test_book: BookProject):
        """6. mock-run invalid chapter returns 404."""
        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "chapter_id": str(uuid4()),
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "chapter_not_found"

    def test_dev_run_real_returns_403_by_default(self, client: TestClient, api_test_book: BookProject, monkeypatch):
        """7. POST /api/books/{book_id}/workflow/dev-run-real returns 403 by default."""
        from app.api import routes_bookrun_workflows
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})

        monkeypatch.setattr(routes_bookrun_workflows, "get_settings", mock_get_settings)

        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/dev-run-real",
            json={
                "workflow_name": "mini_book_pipeline",
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "real_workflow_test_api_disabled"

    def test_disabled_dev_run_real_does_not_call_llm(self, client: TestClient, api_test_book: BookProject, monkeypatch):
        """8. disabled dev-run-real does not call Gemini/OpenAI."""
        from app.api import routes_bookrun_workflows
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})

        monkeypatch.setattr(routes_bookrun_workflows, "get_settings", mock_get_settings)

        call_count = {"count": 0}
        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, input):
            call_count["count"] += 1
            raise RuntimeError("Real LLM called!")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        resp = client.post(
            f"/api/books/{api_test_book.id}/workflow/dev-run-real",
            json={
                "workflow_name": "mini_book_pipeline",
                "build_context_pack": False,
            },
        )
        assert resp.status_code == 403
        assert call_count["count"] == 0
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_get_workflow_run_trace_returns_bundle(self, client: TestClient, api_test_book: BookProject, db: Session):
        """9. GET /api/books/{book_id}/workflow/runs/{run_id}/trace returns trace bundle."""
        # 1. Run a traced workflow first to generate traces
        resp1 = client.post(
            f"/api/books/{api_test_book.id}/workflow/mock-run",
            json={
                "workflow_name": "mini_book_pipeline",
                "traced": True,
                "persist_traces": True,
                "build_context_pack": False,
            },
        )
        assert resp1.status_code == 200
        run_id = resp1.json()["run_id"]

        # 2. Retrieve trace bundle
        resp2 = client.get(
            f"/api/books/{api_test_book.id}/workflow/runs/{run_id}/trace"
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert "traces" in data
        assert "prompt_logs" in data
        assert "token_cost_ledger" in data
        assert len(data["traces"]) == 5

    def test_openapi_includes_endpoints(self, client: TestClient):
        """10. OpenAPI includes new book workflow endpoints."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/books/{book_id}/workflow/mock-run" in paths
        assert "/api/books/{book_id}/workflow/dev-run-real" in paths
        assert "/api/books/{book_id}/workflow/runs/{run_id}/trace" in paths
