"""
AIuthor Backend Tests — Agent Routing and API Endpoints (Module 7.0B).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.config import get_settings


def test_get_agents_returns_eight_agents(client: TestClient):
    """Verify GET /api/agents lists all 8 agents successfully."""
    response = client.get("/api/agents")
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 8
    names = [agent["agent_name"] for agent in data]
    for expected in ["planner", "researcher", "writer", "humanizer", "editor", "fact_checker", "memory_keeper", "assembler"]:
        assert expected in names


def test_get_agent_by_name_returns_details(client: TestClient):
    """Verify GET /api/agents/{agent_name} returns correct details for a registered agent."""
    response = client.get("/api/agents/planner")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["agent_name"] == "planner"
    assert data["display_name"] == "Planner Agent"
    assert "Planner" in data["prompt_template"]


def test_get_agent_by_name_invalid_returns_404(client: TestClient):
    """Verify GET /api/agents/{agent_name} returns 404 for an unregistered name."""
    response = client.get("/api/agents/invalid_agent_name")
    assert response.status_code == 404, response.text
    assert "not registered" in response.json()["detail"]["message"]


def test_post_render_prompt_returns_rendered_content(client: TestClient):
    """Verify POST /api/agents/render-prompt returns rendered system/user prompts."""
    payload = {
        "agent_name": "planner",
        "task": "Outline standard workflows.",
        "context": {"key": "value"},
    }
    response = client.post("/api/agents/render-prompt", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["agent_name"] == "planner"
    assert "Planner" in data["system_prompt"]
    assert "Outline standard workflows." in data["user_prompt"]
    assert '"key": "value"' in data["user_prompt"]


def test_post_render_prompt_does_not_call_llm(client: TestClient, monkeypatch):
    """Verify rendering prompts is a local template function that never contacts LLM providers."""
    # Temporarily monkeypatch generate_text to fail to prove it is not called
    from app.services.llm_service import LLMService

    def mock_generate(*args, **kwargs):
        raise RuntimeError("LLM service called incorrectly!")

    monkeypatch.setattr(LLMService, "generate_text", mock_generate)

    payload = {
        "agent_name": "planner",
        "task": "Test local rendering.",
    }
    response = client.post("/api/agents/render-prompt", json=payload)
    assert response.status_code == 200
    assert "Test local rendering." in response.json()["user_prompt"]


def test_post_mock_run_returns_mock_agent_output(client: TestClient):
    """Verify POST /api/agents/mock-run runs the agent under mock execution mode."""
    payload = {
        "agent_name": "planner",
        "task": "Write outline for RAG.",
    }
    response = client.post("/api/agents/mock-run", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["agent_name"] == "planner"
    assert data["status"] == "completed"
    assert "Mock response for" in data["content"]
    assert data["metadata"]["execution_mode"] == "mock"


def test_post_mock_run_planner_works(client: TestClient):
    """Verify mock run handles planner execution."""
    payload = {
        "agent_name": "planner",
        "task": "Generate RAG guide.",
    }
    response = client.post("/api/agents/mock-run", json=payload)
    assert response.status_code == 200, response.text
    assert "Mock response for" in response.json()["content"]


def test_post_mock_run_writer_works(client: TestClient):
    """Verify mock run handles writer execution with nested payload context."""
    payload = {
        "agent_name": "writer",
        "task": "Draft chapter 1.",
        "context_pack": {"notes": "testing notes"},
        "memory_context": {"context": "empty"},
    }
    response = client.post("/api/agents/mock-run", json=payload)
    assert response.status_code == 200, response.text
    assert "Mock response for" in response.json()["content"]


def test_post_mock_run_invalid_agent_returns_404(client: TestClient):
    """Verify mock execution of an invalid agent returns 404."""
    payload = {
        "agent_name": "unknown_agent",
        "task": "Do nothing",
    }
    response = client.post("/api/agents/mock-run", json=payload)
    assert response.status_code == 404, response.text
    assert "not registered" in response.json()["detail"]["message"]


def test_post_dev_run_real_forbidden_by_default(client: TestClient):
    """Verify POST /api/agents/dev-run-real returns 403 Forbidden when flag is disabled."""
    # Ensure default settings has enable_real_agent_test_api = False in tests
    settings = get_settings()
    assert settings.enable_real_agent_test_api is False

    payload = {
        "agent_name": "planner",
        "task": "Create blueprint",
    }
    response = client.post("/api/agents/dev-run-real", json=payload)
    assert response.status_code == 403, response.text
    assert "Real agent test API is disabled" in response.json()["detail"]


def test_dev_run_real_disabled_does_not_call_gemini_openai(client: TestClient, monkeypatch):
    """Verify that a forbidden call to dev-run-real exits early without contacting LLMs."""
    from app.services.llm_service import LLMService

    def mock_generate(*args, **kwargs):
        raise RuntimeError("LLM service called incorrectly!")

    monkeypatch.setattr(LLMService, "generate_text", mock_generate)

    payload = {
        "agent_name": "planner",
        "task": "Create outline",
    }
    response = client.post("/api/agents/dev-run-real", json=payload)
    assert response.status_code == 403


def test_openapi_includes_agent_paths(client: TestClient):
    """Verify that OpenAPI schemas register the correct routes."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/agents" in paths
    assert "/api/agents/{agent_name}" in paths
    assert "/api/agents/render-prompt" in paths
    assert "/api/agents/mock-run" in paths
    assert "/api/agents/dev-run-real" in paths


def test_static_routes_not_swallowed_by_dynamic_routes(client: TestClient):
    """Assert that Starlette route priority executes static paths first instead of path parameter matching."""
    # Make calls to static paths. If they are swallowed, they would attempt to fetch an agent named "render-prompt"
    # and return 404 (since no such agent exists). Returning 200/403 confirms routing isolation.
    response = client.post("/api/agents/render-prompt", json={"agent_name": "planner", "task": "hello"})
    assert response.status_code == 200

    response = client.post("/api/agents/mock-run", json={"agent_name": "planner", "task": "hello"})
    assert response.status_code == 200

    response = client.post("/api/agents/dev-run-real", json={"agent_name": "planner", "task": "hello"})
    assert response.status_code == 403


def test_no_endpoint_exposes_full_workflow_generation(client: TestClient):
    """Confirm no endpoint in agent routes attempts to execute LangGraph workflow orchestration."""
    # Only individual agents once or render is allowed
    paths = client.get("/openapi.json").json()["paths"]
    for path in paths:
        if path.startswith("/api/agents"):
            # Ensure no workflow or full generation routes
            assert "workflow" not in path
            assert "generate-book" not in path
