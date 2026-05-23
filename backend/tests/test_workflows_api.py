"""
AIuthor Backend Tests — Workflow API Endpoints (Module 7.1A).

Tests that:
1. GET  /api/workflows           → lists registered workflows.
2. GET  /api/workflows/{name}    → returns metadata for known workflow.
3. GET  /api/workflows/{name}    → returns 404 for unknown workflow.
4. POST /api/workflows/mock-run  → runs mock pipeline, returns 5 steps.
5. POST /api/workflows/dev-run-real → returns 403 when flag is disabled.
"""
from __future__ import annotations

import pytest
from httpx import Client

from app.config import get_settings


class TestWorkflowListEndpoint:
    def test_list_workflows_200(self, client: Client):
        """GET /api/workflows returns 200 with a list."""
        res = client.get("/api/workflows")
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert len(body) >= 1

    def test_list_workflows_contains_mini_book_pipeline(self, client: Client):
        """List result must include mini_book_pipeline."""
        res = client.get("/api/workflows")
        assert res.status_code == 200
        names = [wf["workflow_name"] for wf in res.json()]
        assert "mini_book_pipeline" in names

    def test_list_workflows_schema_fields(self, client: Client):
        """Each workflow entry must have required schema fields."""
        res = client.get("/api/workflows")
        assert res.status_code == 200
        for wf in res.json():
            assert "workflow_name" in wf
            assert "display_name" in wf
            assert "description" in wf
            assert "nodes" in wf
            assert isinstance(wf["nodes"], list)


class TestWorkflowInfoEndpoint:
    def test_get_known_workflow_200(self, client: Client):
        """GET /api/workflows/mini_book_pipeline returns 200."""
        res = client.get("/api/workflows/mini_book_pipeline")
        assert res.status_code == 200
        body = res.json()
        assert body["workflow_name"] == "mini_book_pipeline"

    def test_get_known_workflow_has_five_nodes(self, client: Client):
        """mini_book_pipeline must have exactly 5 nodes."""
        res = client.get("/api/workflows/mini_book_pipeline")
        assert res.status_code == 200
        assert len(res.json()["nodes"]) == 5

    def test_get_known_workflow_nodes_correct(self, client: Client):
        """Returned nodes must match expected 5-node pipeline."""
        res = client.get("/api/workflows/mini_book_pipeline")
        assert res.status_code == 200
        nodes = set(res.json()["nodes"])
        expected = {"planner", "researcher", "writer", "editor", "fact_checker"}
        assert nodes == expected

    def test_get_unknown_workflow_404(self, client: Client):
        """GET /api/workflows/unknown returns 404."""
        res = client.get("/api/workflows/unknown_workflow_xyz")
        assert res.status_code == 404

    def test_get_known_workflow_supports_mock(self, client: Client):
        """mini_book_pipeline must advertise supports_mock=true."""
        res = client.get("/api/workflows/mini_book_pipeline")
        assert res.status_code == 200
        assert res.json()["supports_mock"] is True


class TestWorkflowMockRunEndpoint:
    def test_mock_run_200(self, client: Client):
        """POST /api/workflows/mock-run returns 200."""
        payload = {"topic": "Introduction to machine learning"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200

    def test_mock_run_returns_workflow_output(self, client: Client):
        """mock-run returns complete WorkflowOutput JSON."""
        payload = {"topic": "Introduction to climate science"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert "workflow_name" in body
        assert "status" in body
        assert "steps" in body

    def test_mock_run_status_completed(self, client: Client):
        """mock-run returns status='completed' on success."""
        payload = {"topic": "Neural networks explained"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

    def test_mock_run_has_five_steps(self, client: Client):
        """mock-run executes all 5 nodes and returns exactly 5 steps."""
        payload = {"topic": "Cybersecurity fundamentals"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        assert len(res.json()["steps"]) == 5

    def test_mock_run_step_agent_names(self, client: Client):
        """All 5 expected agent names appear in the steps."""
        payload = {"topic": "Software design patterns"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        names = [step["agent_name"] for step in res.json()["steps"]]
        expected = ["planner", "researcher", "writer", "editor", "fact_checker"]
        assert names == expected

    def test_mock_run_all_steps_completed(self, client: Client):
        """Every step in mock-run response has status='completed'."""
        payload = {"topic": "Modern database systems"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        for step in res.json()["steps"]:
            assert step["status"] == "completed"

    def test_mock_run_has_final_content(self, client: Client):
        """mock-run response includes non-empty final_content."""
        payload = {"topic": "Introduction to robotics"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body.get("final_content") is not None
        assert len(body["final_content"]) > 0

    def test_mock_run_metadata_has_execution_mode(self, client: Client):
        """mock-run response metadata contains execution_mode='mock'."""
        payload = {"topic": "Microservices architecture"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body.get("metadata", {}).get("execution_mode") == "mock"

    def test_mock_run_accepts_full_payload(self, client: Client):
        """mock-run accepts all optional fields without error."""
        payload = {
            "topic": "Deep learning for NLP",
            "genre": "technical",
            "reader_profile": "data scientists and ML engineers",
            "tone": "precise and authoritative",
            "workflow_name": "mini_book_pipeline",
            "context_pack": {"context_text": "NLP research summary", "citations": ["paper1"]},
            "memory_context": {"past_chapters": ["Chapter 1: Intro"]},
            "metadata": {"user_id": "test-user-001"},
        }
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

    def test_mock_run_missing_topic_422(self, client: Client):
        """mock-run with missing topic returns 422 validation error."""
        payload = {"genre": "non-fiction"}
        res = client.post("/api/workflows/mock-run", json=payload)
        assert res.status_code == 422

    def test_mock_run_empty_body_422(self, client: Client):
        """mock-run with empty body returns 422 validation error."""
        res = client.post("/api/workflows/mock-run", json={})
        assert res.status_code == 422


class TestWorkflowDevRunRealEndpoint:
    def test_dev_run_real_returns_403_when_disabled(self, client: Client):
        """POST /api/workflows/dev-run-real returns 403 when ENABLE_REAL_WORKFLOW_TEST_API=false."""
        # In test env, ENABLE_REAL_WORKFLOW_TEST_API must always be false
        settings = get_settings()
        assert settings.enable_real_workflow_test_api is False

        payload = {"topic": "DevOps automation principles"}
        res = client.post("/api/workflows/dev-run-real", json=payload)
        assert res.status_code == 403

    def test_dev_run_real_403_body_contains_message(self, client: Client):
        """403 response from dev-run-real includes a descriptive error message."""
        payload = {"topic": "API design principles"}
        res = client.post("/api/workflows/dev-run-real", json=payload)
        assert res.status_code == 403
        # FastAPI detail is either a string or dict
        body = res.json()
        assert "detail" in body
