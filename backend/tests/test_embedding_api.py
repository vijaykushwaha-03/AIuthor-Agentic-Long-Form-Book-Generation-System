"""
AIuthor Backend — Tests: Embedding API Routes (Module 6.0A).

Tests for:
  GET  /api/embeddings/provider
  POST /api/embeddings/mock

IMPORTANT:
  - No test calls Gemini or OpenAI APIs.
  - No test requires real API keys.
  - All tests pass offline.
"""
from __future__ import annotations

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/embeddings/provider
# ─────────────────────────────────────────────────────────────────────────────

class TestGetEmbeddingProviderInfo:
    """Tests for GET /api/embeddings/provider."""

    def test_returns_200(self, client):
        resp = client.get("/api/embeddings/provider")
        assert resp.status_code == 200

    def test_response_has_provider_field(self, client):
        resp = client.get("/api/embeddings/provider")
        data = resp.json()
        assert "provider" in data
        assert isinstance(data["provider"], str)

    def test_response_has_model_field(self, client):
        resp = client.get("/api/embeddings/provider")
        data = resp.json()
        assert "model" in data

    def test_response_has_dimensions_field(self, client):
        resp = client.get("/api/embeddings/provider")
        data = resp.json()
        assert "dimensions" in data
        assert isinstance(data["dimensions"], int)
        assert data["dimensions"] > 0

    def test_response_has_configured_field(self, client):
        resp = client.get("/api/embeddings/provider")
        data = resp.json()
        assert "configured" in data
        assert isinstance(data["configured"], bool)

    def test_response_has_supports_batching_field(self, client):
        resp = client.get("/api/embeddings/provider")
        data = resp.json()
        assert "supports_batching" in data

    def test_no_api_key_required(self, client):
        """Endpoint must return 200 even without any embedding API key set."""
        resp = client.get("/api/embeddings/provider")
        assert resp.status_code == 200

    def test_provider_is_mock_in_test_env(self, client):
        """conftest sets EMBEDDING_PROVIDER=mock."""
        resp = client.get("/api/embeddings/provider")
        data = resp.json()
        # In test env, EMBEDDING_PROVIDER=mock is set by conftest
        assert data["provider"] == "mock"
        assert data["configured"] is True


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/embeddings/mock
# ─────────────────────────────────────────────────────────────────────────────

class TestMockEmbed:
    """Tests for POST /api/embeddings/mock."""

    def _payload(self, texts: list[str] | None = None) -> dict:
        return {"texts": texts or ["Embed this text."]}

    def test_returns_200(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        assert resp.status_code == 200

    def test_response_provider_is_mock(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        assert resp.json()["provider"] == "mock"

    def test_response_model_is_mock_embedding(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        assert resp.json()["model"] == "mock-embedding"

    def test_response_has_items(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1

    def test_item_has_embedding_vector(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        item = resp.json()["items"][0]
        assert "embedding" in item
        assert isinstance(item["embedding"], list)
        assert len(item["embedding"]) > 0

    def test_embedding_values_are_floats(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        embedding = resp.json()["items"][0]["embedding"]
        assert all(isinstance(v, (int, float)) for v in embedding)

    def test_response_has_dimensions(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        data = resp.json()
        assert "dimensions" in data
        assert isinstance(data["dimensions"], int)
        assert data["dimensions"] > 0

    def test_dimensions_matches_embedding_length(self, client):
        resp = client.post("/api/embeddings/mock", json=self._payload())
        data = resp.json()
        dims = data["dimensions"]
        embedding_len = len(data["items"][0]["embedding"])
        assert dims == embedding_len

    def test_multiple_texts_return_multiple_items(self, client):
        payload = {"texts": ["First.", "Second.", "Third."]}
        resp = client.post("/api/embeddings/mock", json=payload)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 3

    def test_rejects_empty_texts_list(self, client):
        resp = client.post("/api/embeddings/mock", json={"texts": []})
        assert resp.status_code == 422

    def test_rejects_empty_string_in_texts(self, client):
        resp = client.post("/api/embeddings/mock", json={"texts": ["valid", ""]})
        assert resp.status_code == 422

    def test_deterministic_same_text_same_vector(self, client):
        payload = {"texts": ["Consistent text for determinism check."]}
        r1 = client.post("/api/embeddings/mock", json=payload).json()["items"][0]["embedding"]
        r2 = client.post("/api/embeddings/mock", json=payload).json()["items"][0]["embedding"]
        assert r1 == r2

    def test_with_metadata(self, client):
        payload = {"texts": ["Hello."], "metadata": {"book_id": "test-001"}}
        resp = client.post("/api/embeddings/mock", json=payload)
        assert resp.status_code == 200
        assert resp.json()["metadata"] == {"book_id": "test-001"}


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI Schema Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAPISchemaEmbeddings:
    """Verify embedding routes appear in the OpenAPI spec."""

    def test_openapi_includes_provider_endpoint(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert "/api/embeddings/provider" in paths

    def test_openapi_includes_mock_endpoint(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json().get("paths", {})
        assert "/api/embeddings/mock" in paths

    def test_provider_endpoint_has_get_method(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json().get("paths", {})
        assert "get" in paths.get("/api/embeddings/provider", {})

    def test_mock_endpoint_has_post_method(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json().get("paths", {})
        assert "post" in paths.get("/api/embeddings/mock", {})
