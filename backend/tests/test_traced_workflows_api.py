"""
AIuthor Backend Tests — Traced Workflows API Routes (Module 7.1B).
"""
from __future__ import annotations

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, AgentTrace, PromptLog
from app.config import Settings


class TestTracedWorkflowsAPI:

    def test_mock_run_traced_api_returns_200(self, client: TestClient):
        """POST /api/workflows/mock-run-traced returns 200 OK and populated WorkflowTraceResponse."""
        resp = client.post(
            "/api/workflows/mock-run-traced",
            json={
                "topic": "CSS Styling Best Practices",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["workflow_name"] == "mini_book_pipeline"
        assert data["status"] == "completed"
        assert data["execution_mode"] == "mock"
        assert len(data["steps"]) == 5

    def test_mock_run_traced_api_persists_traces(self, client: TestClient, db: Session):
        """POST /api/workflows/mock-run-traced writes traces to database when persist_traces=True."""
        resp = client.post(
            "/api/workflows/mock-run-traced",
            json={
                "topic": "Refactoring Legacy Databases",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        assert run_id is not None

        db_traces = db.query(AgentTrace).filter(AgentTrace.run_id == run_id).all()
        assert len(db_traces) == 5

    def test_mock_run_traced_api_does_not_call_real_llm(self, client: TestClient, monkeypatch):
        """POST /api/workflows/mock-run-traced operates fully offline."""
        call_count = {"count": 0}

        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, inp):
            call_count["count"] += 1
            raise RuntimeError("Called real LLM in mock test")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        resp = client.post(
            "/api/workflows/mock-run-traced",
            json={
                "topic": "Micro-animations in UX design",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 200
        assert call_count["count"] == 0
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_dev_run_real_traced_returns_403_by_default(self, client: TestClient, monkeypatch):
        """POST /api/workflows/dev-run-real-traced returns 403 Forbidden by default."""
        from app.api import routes_workflows
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_workflows, "get_settings", mock_get_settings)

        resp = client.post(
            "/api/workflows/dev-run-real-traced",
            json={
                "topic": "Real LLM calling",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 403
        assert "disabled" in resp.json()["detail"].lower()

    def test_disabled_dev_run_real_traced_does_not_call_real_llm(self, client: TestClient, monkeypatch):
        """Forbidden live execution does not make any real LLM calls."""
        from app.api import routes_workflows
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_workflows, "get_settings", mock_get_settings)

        call_count = {"count": 0}

        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, inp):
            call_count["count"] += 1
            raise RuntimeError("Real LLM called")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        resp = client.post(
            "/api/workflows/dev-run-real-traced",
            json={
                "topic": "Forbidden LLM test",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 403
        assert call_count["count"] == 0
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_get_workflow_trace_bundle_returns_traces(self, client: TestClient, db: Session):
        """GET /api/workflows/traces/{run_id} returns compiled database traces."""
        # Create a project and run
        proj = BookProject(
            topic="Lore Concepts",
            reader_profile="general",
            genre="fiction",
            tone="dramatic",
            target_chapters=3,
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)

        run = BookRun(
            book_id=proj.id,
            status="completed",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Add a mock trace row
        trace = AgentTrace(
            run_id=run.id,
            book_id=proj.id,
            agent_name="planner",
            status="completed",
        )
        db.add(trace)
        db.commit()

        resp = client.get(f"/api/workflows/traces/{run.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == str(run.id)
        assert len(data["traces"]) == 1
        assert data["traces"][0]["agent_name"] == "planner"

    def test_get_workflow_trace_bundle_returns_404_for_unknown_run(self, client: TestClient):
        """GET /api/workflows/traces/{run_id} returns 404 for non-existent run ID."""
        random_id = uuid.uuid4()
        resp = client.get(f"/api/workflows/traces/{random_id}")
        assert resp.status_code == 404
        assert "run_not_found" in resp.json()["detail"]["code"]

    def test_openapi_includes_new_traced_paths(self, client: TestClient):
        """Verify new traced workflow routes are listed in the app's OpenAPI schema."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/workflows/mock-run-traced" in paths
        assert "/api/workflows/dev-run-real-traced" in paths
        assert "/api/workflows/traces/{run_id}" in paths

    def test_static_trace_routes_not_swallowed_by_dynamic_workflow_route(self, client: TestClient):
        """Verify /api/workflows/traces/{run_id} is evaluated correctly and not swallowed by /{workflow_name}."""
        # Querying an invalid workflow name returns 404 workflow_not_found
        resp_wf = client.get("/api/workflows/traces")
        assert resp_wf.status_code == 404
        assert "workflow_not_found" in resp_wf.json()["detail"]["code"]

        # Querying traces/{run_id} returns 404 run_not_found (proves it hits the trace bundle route and not the workflow dynamic route)
        random_id = uuid.uuid4()
        resp_tr = client.get(f"/api/workflows/traces/{random_id}")
        assert resp_tr.status_code == 404
        assert "run_not_found" in resp_tr.json()["detail"]["code"]
