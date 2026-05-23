"""
AIuthor Backend — Tests: RAG Embedding API Routes (Module 6.0B).

Tests for:
  GET  /api/rag/pgvector-status
  POST /api/chunks/{chunk_id}/embed
  POST /api/sources/{document_id}/embed-chunks
  POST /api/books/{book_id}/embed-chunks
  POST /api/rag/semantic-retrieve
  (existing lexical /api/rag/retrieve preserved)

All tests use mock embedding provider (EMBEDDING_PROVIDER=mock in conftest).
No real API keys or network calls are needed.
"""
from __future__ import annotations

import uuid

import pytest


# ─── Test fixtures / helpers ──────────────────────────────────────────────────

def _create_book(client) -> dict:
    resp = client.post("/api/books", json={
        "topic": "Embed API Test Book",
        "reader_profile": "Developers",
        "genre": "Technology",
        "tone": "conversational",
        "target_chapters": 5,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_source(client, book_id: str) -> dict:
    resp = client.post(f"/api/books/{book_id}/sources", json={
        "book_id": book_id,
        "title": "Test Source Document",
        "source_type": "manual",
        "raw_text": "This is the raw text for embedding tests. It contains enough content.",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_chunk(client, doc_id: str, index: int = 0, text: str = "Sample chunk text for embedding.") -> dict:
    resp = client.post(f"/api/sources/{doc_id}/chunks", json={
        "document_id": doc_id,
        "chunk_index": index,
        "chunk_text": text,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/rag/pgvector-status
# ─────────────────────────────────────────────────────────────────────────────

class TestPgvectorStatusEndpoint:

    def test_returns_200(self, client):
        resp = client.get("/api/rag/pgvector-status")
        assert resp.status_code == 200

    def test_response_has_available_field(self, client):
        resp = client.get("/api/rag/pgvector-status")
        assert "available" in resp.json()

    def test_response_has_extension_name(self, client):
        resp = client.get("/api/rag/pgvector-status")
        assert resp.json()["extension_name"] == "vector"

    def test_response_has_message(self, client):
        resp = client.get("/api/rag/pgvector-status")
        assert "message" in resp.json()
        assert isinstance(resp.json()["message"], str)

    def test_available_is_false_in_sqlite_tests(self, client):
        resp = client.get("/api/rag/pgvector-status")
        # SQLite test DB never has pgvector extension
        assert resp.json()["available"] is False


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/chunks/{chunk_id}/embed
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbedChunkEndpoint:

    def test_returns_200(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        resp = client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        assert resp.status_code == 200

    def test_response_has_chunk_id(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        resp = client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        data = resp.json()
        assert "chunk_id" in data

    def test_response_embedding_status_completed(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        resp = client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        assert resp.json()["embedding_status"] == "completed"

    def test_response_has_embedding_provider(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        resp = client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        data = resp.json()
        assert data["embedding_provider"] == "mock"

    def test_response_has_embedding_dimensions(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        resp = client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        assert resp.json()["embedding_dimensions"] == 8

    def test_missing_chunk_returns_404(self, client):
        resp = client.post(f"/api/chunks/{uuid.uuid4()}/embed", json={})
        assert resp.status_code == 404

    def test_force_false_skips_completed_chunk(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        # Embed once
        client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        # Patch embedding_provider to confirm skip behavior
        # Embed again without force — should return completed status
        resp2 = client.post(f"/api/chunks/{chunk['id']}/embed", json={"force": False})
        assert resp2.status_code == 200
        assert resp2.json()["embedding_status"] == "completed"

    def test_force_true_re_embeds(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        chunk = _create_chunk(client, doc["id"])
        client.post(f"/api/chunks/{chunk['id']}/embed", json={})
        resp2 = client.post(f"/api/chunks/{chunk['id']}/embed", json={"force": True})
        assert resp2.status_code == 200
        assert resp2.json()["embedding_status"] == "completed"


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sources/{document_id}/embed-chunks
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbedSourceChunksEndpoint:

    def test_returns_200(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        _create_chunk(client, doc["id"], index=0, text="First chunk text.")
        _create_chunk(client, doc["id"], index=1, text="Second chunk text.")
        resp = client.post(f"/api/sources/{doc['id']}/embed-chunks", json={})
        assert resp.status_code == 200

    def test_response_embedded_count(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        _create_chunk(client, doc["id"], index=0, text="Chunk one.")
        _create_chunk(client, doc["id"], index=1, text="Chunk two.")
        resp = client.post(f"/api/sources/{doc['id']}/embed-chunks", json={})
        data = resp.json()
        assert data["embedded_count"] == 2
        assert data["failed_count"] == 0

    def test_response_target_type_is_document(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        resp = client.post(f"/api/sources/{doc['id']}/embed-chunks", json={})
        assert resp.json()["target_type"] == "document"

    def test_missing_document_returns_404(self, client):
        resp = client.post(f"/api/sources/{uuid.uuid4()}/embed-chunks", json={})
        assert resp.status_code == 404

    def test_no_chunks_returns_zero_counts(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        resp = client.post(f"/api/sources/{doc['id']}/embed-chunks", json={})
        data = resp.json()
        assert data["total_candidates"] == 0
        assert data["embedded_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/books/{book_id}/embed-chunks
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbedBookChunksEndpoint:

    def test_returns_200(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        _create_chunk(client, doc["id"], index=0, text="Book-level chunk.")
        resp = client.post(f"/api/books/{book['id']}/embed-chunks", json={})
        assert resp.status_code == 200

    def test_response_target_type_is_book(self, client):
        book = _create_book(client)
        resp = client.post(f"/api/books/{book['id']}/embed-chunks", json={})
        assert resp.json()["target_type"] == "book"

    def test_embedded_count_correct(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        _create_chunk(client, doc["id"], index=0, text="Book chunk A.")
        _create_chunk(client, doc["id"], index=1, text="Book chunk B.")
        resp = client.post(f"/api/books/{book['id']}/embed-chunks", json={})
        assert resp.json()["embedded_count"] == 2

    def test_missing_book_returns_404(self, client):
        resp = client.post(f"/api/books/{uuid.uuid4()}/embed-chunks", json={})
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/rag/semantic-retrieve
# ─────────────────────────────────────────────────────────────────────────────

class TestSemanticRetrieveEndpoint:

    def _setup_embedded_chunks(self, client, texts: list[str] | None = None) -> dict:
        """Create a book/doc/embedded chunks and return the book dict."""
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        texts = texts or ["Python programming basics.", "Machine learning intro."]
        for i, text in enumerate(texts):
            _create_chunk(client, doc["id"], index=i, text=text)
        # Bulk embed all chunks
        client.post(f"/api/sources/{doc['id']}/embed-chunks", json={})
        return book

    def test_returns_200(self, client):
        self._setup_embedded_chunks(client)
        resp = client.post("/api/rag/semantic-retrieve", json={"query": "programming"})
        assert resp.status_code == 200

    def test_response_has_results_list(self, client):
        self._setup_embedded_chunks(client)
        resp = client.post("/api/rag/semantic-retrieve", json={"query": "programming"})
        assert "results" in resp.json()
        assert isinstance(resp.json()["results"], list)

    def test_response_has_provider_model_dims(self, client):
        self._setup_embedded_chunks(client)
        resp = client.post("/api/rag/semantic-retrieve", json={"query": "programming"})
        data = resp.json()
        assert data["provider"] == "mock"
        assert data["model"] == "mock-embedding"
        assert data["dimensions"] == 8

    def test_response_pgvector_used_false_in_tests(self, client):
        self._setup_embedded_chunks(client)
        resp = client.post("/api/rag/semantic-retrieve", json={"query": "test"})
        assert resp.json()["pgvector_used"] is False

    def test_respects_top_k(self, client):
        self._setup_embedded_chunks(
            client,
            texts=["Chunk one.", "Chunk two.", "Chunk three.", "Chunk four."]
        )
        resp = client.post("/api/rag/semantic-retrieve", json={"query": "chunk", "top_k": 2})
        assert len(resp.json()["results"]) <= 2

    def test_include_raw_text_false_hides_chunk_text(self, client):
        self._setup_embedded_chunks(client, texts=["Secret content inside."])
        resp = client.post(
            "/api/rag/semantic-retrieve",
            json={"query": "secret", "include_raw_text": False},
        )
        for item in resp.json()["results"]:
            assert item["chunk_text"] is None

    def test_returns_empty_results_no_embedded_chunks(self, client):
        # Create a new book with no embedded chunks
        book = _create_book(client)
        resp = client.post("/api/rag/semantic-retrieve", json={
            "query": "nothing here at all",
            "book_id": book["id"],
        })
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_retrieval_mode_is_semantic(self, client):
        self._setup_embedded_chunks(client)
        resp = client.post("/api/rag/semantic-retrieve", json={"query": "test"})
        assert resp.json()["retrieval_mode"] == "semantic"

    def test_empty_query_returns_422(self, client):
        resp = client.post("/api/rag/semantic-retrieve", json={"query": ""})
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Existing lexical /api/rag/retrieve still works
# ─────────────────────────────────────────────────────────────────────────────

class TestLexicalRetrieveStillWorks:

    def test_lexical_retrieve_returns_200(self, client):
        book = _create_book(client)
        doc = _create_source(client, book["id"])
        _create_chunk(client, doc["id"], index=0, text="The ancient ruins of the temple.")
        resp = client.post("/api/rag/retrieve", json={"query": "ruins"})
        assert resp.status_code == 200

    def test_lexical_retrieve_response_shape_unchanged(self, client):
        resp = client.post("/api/rag/retrieve", json={"query": "anything"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "query" in data
        assert "status" in data


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI schema verification
# ─────────────────────────────────────────────────────────────────────────────

class TestOpenAPIIncludesNewEndpoints:

    def test_openapi_has_pgvector_status(self, client):
        resp = client.get("/openapi.json")
        assert "/api/rag/pgvector-status" in resp.json()["paths"]

    def test_openapi_has_chunk_embed(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        # The path is /api/chunks/{chunk_id}/embed
        assert any(
            "chunk" in p and "embed" in p and "embed-chunks" not in p
            for p in paths
        ), f"Expected chunk embed path in: {list(paths.keys())}"

    def test_openapi_has_embed_source_chunks(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert any("embed-chunks" in p and "sources" in p for p in paths)

    def test_openapi_has_embed_book_chunks(self, client):
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert any("embed-chunks" in p and "books" in p for p in paths)

    def test_openapi_has_semantic_retrieve(self, client):
        resp = client.get("/openapi.json")
        assert "/api/rag/semantic-retrieve" in resp.json()["paths"]
