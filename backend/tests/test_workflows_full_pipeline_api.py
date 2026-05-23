"""
AIuthor Backend Tests — Multi-Workflow API Routing & Gating (Module 7.2A).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AgentTrace


class TestWorkflowsFullPipelineAPI:

    def test_get_workflows_returns_both_names(self, client: TestClient):
        """GET /api/workflows lists both pipelines in metadata."""
        resp = client.get("/api/workflows")
        assert resp.status_code == 200
        data = resp.json()
        names = [w["workflow_name"] for w in data]
        assert "mini_book_pipeline" in names
        assert "full_agent_pipeline" in names

    def test_get_workflow_info_full_agent_pipeline(self, client: TestClient):
        """GET /api/workflows/full_agent_pipeline returns workflow info and node list."""
        resp = client.get("/api/workflows/full_agent_pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_name"] == "full_agent_pipeline"
        assert len(data["nodes"]) == 8
        assert "humanizer" in data["nodes"]

    def test_post_mock_run_with_full_agent_pipeline(self, client: TestClient):
        """POST /api/workflows/mock-run executes full 8-node mock pipeline."""
        resp = client.post(
            "/api/workflows/mock-run",
            json={
                "topic": "Microservices vs Monoliths",
                "workflow_name": "full_agent_pipeline",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["workflow_name"] == "full_agent_pipeline"
        assert len(data["steps"]) == 8
        assert data["steps"][-1]["agent_name"] == "assembler"

    def test_post_mock_run_traced_with_full_agent_pipeline(self, client: TestClient):
        """POST /api/workflows/mock-run-traced executes full 8-node traced mock pipeline."""
        resp = client.post(
            "/api/workflows/mock-run-traced",
            json={
                "topic": "Continuous Delivery pipelines",
                "workflow_name": "full_agent_pipeline",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_name"] == "full_agent_pipeline"
        assert len(data["steps"]) == 8
        assert data["steps"][-1]["agent_name"] == "assembler"
        assert data["steps"][-1]["trace_id"] is not None

    def test_mock_run_traced_full_pipeline_persists_traces(self, client: TestClient, db: Session):
        """POST /api/workflows/mock-run-traced writes 8 AgentTrace rows to the database."""
        resp = client.post(
            "/api/workflows/mock-run-traced",
            json={
                "topic": "NoSQL database scaling",
                "workflow_name": "full_agent_pipeline",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]
        assert run_id is not None

        db_traces = db.query(AgentTrace).filter(AgentTrace.run_id == run_id).all()
        assert len(db_traces) == 8

    def test_post_dev_run_real_with_full_agent_pipeline_returns_403(self, client: TestClient, monkeypatch):
        """POST /api/workflows/dev-run-real with full_agent_pipeline returns 403 Forbidden by default."""
        from app.api import routes_workflows
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_workflows, "get_settings", mock_get_settings)

        resp = client.post(
            "/api/workflows/dev-run-real",
            json={
                "topic": "Forbidden live run",
                "workflow_name": "full_agent_pipeline",
            },
        )
        assert resp.status_code == 403

    def test_post_dev_run_real_traced_with_full_agent_pipeline_returns_403(self, client: TestClient, monkeypatch):
        """POST /api/workflows/dev-run-real-traced with full_agent_pipeline returns 403 Forbidden by default."""
        from app.api import routes_workflows
        def mock_get_settings():
            from app.config import get_settings as orig_get_settings
            s = orig_get_settings()
            return s.model_copy(update={"enable_real_workflow_test_api": False})
        monkeypatch.setattr(routes_workflows, "get_settings", mock_get_settings)

        resp = client.post(
            "/api/workflows/dev-run-real-traced",
            json={
                "topic": "Forbidden live traced run",
                "workflow_name": "full_agent_pipeline",
                "persist_traces": True,
            },
        )
        assert resp.status_code == 403

    def test_disabled_real_endpoints_do_not_call_real_llm(self, client: TestClient, monkeypatch):
        """Dev real workflows fail immediately without calling live LLMs when disabled."""
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

        resp1 = client.post(
            "/api/workflows/dev-run-real",
            json={
                "topic": "Forbidden run test",
                "workflow_name": "full_agent_pipeline",
            },
        )
        assert resp1.status_code == 403

        resp2 = client.post(
            "/api/workflows/dev-run-real-traced",
            json={
                "topic": "Forbidden run traced test",
                "workflow_name": "full_agent_pipeline",
                "persist_traces": True,
            },
        )
        assert resp2.status_code == 403

        assert call_count["count"] == 0
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_invalid_workflow_name_returns_error(self, client: TestClient):
        """Unsupported workflow_name parameter returns 422 validation error."""
        resp = client.post(
            "/api/workflows/mock-run",
            json={
                "topic": "Invalid workflow topic name",
                "workflow_name": "non_existent_unsupported_pipeline_xyz",
            },
        )
        assert resp.status_code == 422
        # Verify the error detail contains validation info
        assert "value_error" in resp.json()["detail"][0]["type"]
        assert "is not registered or supported" in resp.json()["detail"][0]["msg"]

    def test_openapi_paths_unchanged(self, client: TestClient):
        """All existing REST endpoints paths remain present and identical in OpenAPI schemas."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/workflows" in paths
        assert "/api/workflows/{workflow_name}" in paths
        assert "/api/workflows/mock-run" in paths
        assert "/api/workflows/dev-run-real" in paths
        assert "/api/workflows/mock-run-traced" in paths
        assert "/api/workflows/dev-run-real-traced" in paths
        assert "/api/workflows/traces/{run_id}" in paths
