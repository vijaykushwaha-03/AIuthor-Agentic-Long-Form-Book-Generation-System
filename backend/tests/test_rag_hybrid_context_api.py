"""
AIuthor Backend Tests — RAG Hybrid Retrieval & Context Pack API tests (Module 6.1).

Uses the session-scoped TestClient from conftest.py.
All tests run offline.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

# ── Payload helpers ───────────────────────────────────────────────────────────

def _book_payload(topic="Hybrid API Book") -> dict:
    return {
        "topic": topic,
        "reader_profile": "General",
        "genre": "Science",
        "tone": "conversational",
        "target_chapters": 3,
    }


def _source_payload(book_id: str, title="API Reference", **kw) -> dict:
    return {
        "book_id": book_id,
        "title": title,
        "source_type": "paper",
        "raw_text": "This is a reference document for testing RAG APIs.",
        **kw,
    }


def _chunk_payload(document_id: str, chunk_index: int = 0, text="Chunk payload content.", **kw) -> dict:
    return {
        "document_id": document_id,
        "chunk_index": chunk_index,
        "chunk_text": text,
        **kw,
    }


def _create_book(client: TestClient, topic="Hybrid API Test") -> str:
    resp = client.post("/api/books", json=_book_payload(topic=topic))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_source(client: TestClient, book_id: str, title="API Ref") -> dict:
    resp = client.post(f"/api/books/{book_id}/sources", json=_source_payload(book_id, title=title))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_chunk(client: TestClient, document_id: str, chunk_index: int = 0, text="Content.") -> dict:
    resp = client.post(
        f"/api/sources/{document_id}/chunks",
        json=_chunk_payload(document_id, chunk_index=chunk_index, text=text),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestRAGHybridContextAPI:

    def _setup_book_and_chunks(self, client: TestClient, topic="Hybrid API Chunks") -> tuple[str, str, list[str]]:
        book_id = _create_book(client, topic=topic)
        doc = _create_source(client, book_id, title="Reference Doc")
        
        c1 = _create_chunk(client, doc["id"], chunk_index=0, text="First chunk content of the RAG pipeline.")
        c2 = _create_chunk(client, doc["id"], chunk_index=1, text="Second chunk content with distinct vocabulary.")
        
        # Trigger mock embedding generation using conftest embedding provider setup
        # POST /api/chunks/{chunk_id}/embed
        client.post(f"/api/chunks/{c1['id']}/embed", json={"provider": "mock"})
        client.post(f"/api/chunks/{c2['id']}/embed", json={"provider": "mock"})
        
        return book_id, doc["id"], [c1["id"], c2["id"]]

    def test_hybrid_retrieve_returns_hybrid_response(self, client: TestClient):
        """POST /api/rag/hybrid-retrieve returns a correctly formatted HybridRetrievalResponse."""
        book_id, _, _ = self._setup_book_and_chunks(client, "Hybrid Response Test")
        
        resp = client.post(
            "/api/rag/hybrid-retrieve",
            json={
                "query": "First chunk content",
                "book_id": book_id,
                "top_k": 5,
                "semantic_weight": 0.5,
                "lexical_weight": 0.5,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["query"] == "First chunk content"
        assert data["retrieval_mode"] == "hybrid"
        assert len(data["results"]) >= 1
        assert "citations" in data

    def test_hybrid_response_contains_citations(self, client: TestClient):
        """Citations block contains valid CitationItem sequential entries C1, C2..."""
        book_id, _, _ = self._setup_book_and_chunks(client, "Citations API Test")
        
        resp = client.post(
            "/api/rag/hybrid-retrieve",
            json={
                "query": "Second chunk",
                "book_id": book_id,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        citations = data["citations"]
        assert len(citations) >= 1
        assert citations[0]["citation_id"] == "C1"
        assert citations[0]["source_title"] == "Reference Doc"
        assert citations[0]["retrieval_mode"] in ["hybrid", "semantic", "lexical"]

    def test_hybrid_response_respects_top_k(self, client: TestClient):
        """Caps the results length by top_k."""
        book_id, _, _ = self._setup_book_and_chunks(client, "TopK API Test")
        
        resp = client.post(
            "/api/rag/hybrid-retrieve",
            json={
                "query": "content",
                "book_id": book_id,
                "top_k": 1,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["results"]) == 1
        assert len(data["citations"]) == 1

    def test_context_pack_returns_context_text(self, client: TestClient):
        """POST /api/rag/context-pack generates agent-ready annotated block."""
        book_id, _, _ = self._setup_book_and_chunks(client, "Context Pack API Test")
        
        resp = client.post(
            "/api/rag/context-pack",
            json={
                "query": "distinct vocabulary",
                "book_id": book_id,
                "max_chunks": 3,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["book_id"] == book_id
        assert "context_text" in data
        assert "[C1]" in data["context_text"]
        assert "distinct vocabulary" in data["context_text"]
        assert data["total_chunks"] >= 1
        assert len(data["chunks"]) >= 1

    def test_context_pack_response_contains_citation_markers(self, client: TestClient):
        """ContextPackResponse lists the matching CitationItems."""
        book_id, _, _ = self._setup_book_and_chunks(client, "Markers API Test")
        
        resp = client.post(
            "/api/rag/context-pack",
            json={
                "query": "RAG pipeline",
                "book_id": book_id,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["citations"]) >= 1
        assert data["citations"][0]["citation_id"] == "C1"
        assert data["citations"][0]["source_title"] == "Reference Doc"

    def test_context_pack_respects_max_chunks(self, client: TestClient):
        """Number of packed chunks does not exceed max_chunks."""
        book_id, _, _ = self._setup_book_and_chunks(client, "MaxChunks API Test")
        
        resp = client.post(
            "/api/rag/context-pack",
            json={
                "query": "content",
                "book_id": book_id,
                "max_chunks": 1,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_chunks"] == 1
        assert len(data["chunks"]) == 1

    def test_context_pack_for_missing_book_returns_404(self, client: TestClient):
        """Requesting context block for a missing book project UUID returns 404."""
        fake_id = str(uuid4())
        resp = client.post(
            "/api/rag/context-pack",
            json={
                "query": "test",
                "book_id": fake_id,
            }
        )
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()

    def test_existing_lexical_retrieval_endpoint_still_works(self, client: TestClient):
        """Original POST /api/rag/retrieve remains fully functional and unaffected."""
        book_id, _, _ = self._setup_book_and_chunks(client, "Backwards Lexical Test")
        
        resp = client.post(
            "/api/rag/retrieve",
            json={
                "query": "pipeline",
                "book_id": book_id,
                "top_k": 5,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "results" in data
        assert data["total_results"] >= 1
        assert "lexical" in data["message"].lower()

    def test_existing_semantic_retrieval_endpoint_still_works(self, client: TestClient):
        """Original POST /api/rag/semantic-retrieve remains functional and unaffected."""
        book_id, _, _ = self._setup_book_and_chunks(client, "Backwards Semantic Test")
        
        resp = client.post(
            "/api/rag/semantic-retrieve",
            json={
                "query": "vocabulary",
                "book_id": book_id,
                "top_k": 5,
            }
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["retrieval_mode"] == "semantic"
        assert len(data["results"]) >= 1

    def test_openapi_includes_new_endpoints(self, client: TestClient):
        """OpenAPI json schema documents the new hybrid and context-pack paths."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, resp.text
        spec = resp.json()
        paths = spec["paths"]
        assert "/api/rag/hybrid-retrieve" in paths
        assert "/api/rag/context-pack" in paths
        
        # Verify POST method registrations
        assert "post" in paths["/api/rag/hybrid-retrieve"]
        assert "post" in paths["/api/rag/context-pack"]
