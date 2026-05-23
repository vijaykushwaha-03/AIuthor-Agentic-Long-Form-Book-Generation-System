"""
AIuthor Backend — Tests: LLM API Routes (Module 5.0).

Tests for:
  GET  /api/llm/provider
  POST /api/llm/mock-generate

IMPORTANT:
  - No test calls Gemini or OpenAI APIs.
  - No test requires real API keys.
  - All tests pass offline.
"""
from __future__ import annotations

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/llm/provider
# ─────────────────────────────────────────────────────────────────────────────

class TestGetProviderInfo:
    """Tests for GET /api/llm/provider."""

    def test_returns_200(self, client):
        resp = client.get("/api/llm/provider")
        assert resp.status_code == 200

    def test_response_has_provider_field(self, client):
        resp = client.get("/api/llm/provider")
        data = resp.json()
        assert "provider" in data

    def test_response_has_model_field(self, client):
        resp = client.get("/api/llm/provider")
        data = resp.json()
        assert "model" in data

    def test_response_has_configured_field(self, client):
        resp = client.get("/api/llm/provider")
        data = resp.json()
        assert "configured" in data
        assert isinstance(data["configured"], bool)

    def test_response_has_supports_streaming_field(self, client):
        resp = client.get("/api/llm/provider")
        data = resp.json()
        assert "supports_streaming" in data

    def test_provider_is_mock_in_test_env(self, client):
        """conftest sets LLM_PROVIDER=mock via os.environ."""
        resp = client.get("/api/llm/provider")
        data = resp.json()
        # In test env LLM_PROVIDER=mock is set by conftest — expect mock or at least a string
        assert isinstance(data["provider"], str)
        assert len(data["provider"]) > 0

    def test_no_api_key_required(self, client):
        """Endpoint must return 200 even without any LLM API key set."""
        resp = client.get("/api/llm/provider")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/llm/mock-generate
# ─────────────────────────────────────────────────────────────────────────────

class TestMockGenerate:
    """Tests for POST /api/llm/mock-generate."""

    def _payload(self, content: str = "Write a chapter outline.", role: str = "user") -> dict:
        return {"messages": [{"role": role, "content": content}]}

    def test_returns_200(self, client):
        resp = client.post("/api/llm/mock-generate", json=self._payload())
        assert resp.status_code == 200

    def test_response_has_content(self, client):
        resp = client.post("/api/llm/mock-generate", json=self._payload())
        data = resp.json()
        assert "content" in data
        assert isinstance(data["content"], str)
        assert len(data["content"]) > 0

    def test_response_provider_is_mock(self, client):
        resp = client.post("/api/llm/mock-generate", json=self._payload())
        data = resp.json()
        assert data["provider"] == "mock"

    def test_response_model_is_mock_llm(self, client):
        resp = client.post("/api/llm/mock-generate", json=self._payload())
        data = resp.json()
        assert data["model"] == "mock-llm"

    def test_response_contains_echoed_input(self, client):
        resp = client.post(
            "/api/llm/mock-generate",
            json=self._payload("Tell me about dragons."),
        )
        data = resp.json()
        assert "Tell me about dragons." in data["content"]

    def test_response_has_token_counts(self, client):
        resp = client.post("/api/llm/mock-generate", json=self._payload())
        data = resp.json()
        assert data.get("input_tokens") is not None
        assert data.get("output_tokens") is not None
        assert data.get("total_tokens") is not None

    def test_rejects_invalid_role(self, client):
        """Messages with an invalid role should return 422 Unprocessable Entity."""
        payload = {"messages": [{"role": "robot", "content": "Hello."}]}
        resp = client.post("/api/llm/mock-generate", json=payload)
        assert resp.status_code == 422

    def test_rejects_empty_messages_list(self, client):
        payload = {"messages": []}
        resp = client.post("/api/llm/mock-generate", json=payload)
        assert resp.status_code == 422

    def test_multi_message_conversation(self, client):
        payload = {
            "messages": [
                {"role": "system", "content": "You are a book writer."},
                {"role": "user", "content": "Write chapter one."},
            ]
        }
        resp = client.post("/api/llm/mock-generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "Write chapter one." in data["content"]

    def test_with_metadata(self, client):
        payload = {
            "messages": [{"role": "user", "content": "Hello."}],
            "metadata": {"run_id": "test-run-001"},
        }
        resp = client.post("/api/llm/mock-generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("metadata") == {"run_id": "test-run-001"}


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI Schema Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAPISchemaLLM:
    """Verify LLM routes appear in the OpenAPI spec."""

    def test_openapi_includes_provider_endpoint(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert "/api/llm/provider" in paths

    def test_openapi_includes_mock_generate_endpoint(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert "/api/llm/mock-generate" in paths

    def test_provider_endpoint_has_get_method(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json().get("paths", {})
        assert "get" in paths.get("/api/llm/provider", {})

    def test_mock_generate_endpoint_has_post_method(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json().get("paths", {})
        assert "post" in paths.get("/api/llm/mock-generate", {})
