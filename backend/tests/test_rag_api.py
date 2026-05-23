"""
AIuthor Backend Tests — RAG API route tests.

Uses the session-scoped TestClient from conftest.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


# ── Payload helpers ───────────────────────────────────────────────────────────

def _book_payload(**kw) -> dict:
    return {
        "topic": "RAG Test Book",
        "reader_profile": "Developers",
        "genre": "Technology",
        "tone": "conversational",
        "target_chapters": 5,
        **kw,
    }


def _source_payload(book_id: str, **kw) -> dict:
    return {
        "book_id": book_id,
        "title": "Introduction to Machine Learning",
        "source_type": "paper",
        "raw_text": "Machine learning is a subset of artificial intelligence. " * 10,
        **kw,
    }


def _chunk_payload(document_id: str, chunk_index: int = 0, **kw) -> dict:
    return {
        "document_id": document_id,
        "chunk_index": chunk_index,
        "chunk_text": "Machine learning is a subset of artificial intelligence.",
        **kw,
    }


def _create_book(client: TestClient, topic="RAG API Test") -> str:
    resp = client.post("/api/books", json=_book_payload(topic=topic))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_source(client: TestClient, book_id: str, **kw) -> dict:
    resp = client.post(f"/api/books/{book_id}/sources", json=_source_payload(book_id, **kw))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_chunk(client: TestClient, document_id: str, chunk_index: int = 0, **kw) -> dict:
    resp = client.post(
        f"/api/sources/{document_id}/chunks",
        json=_chunk_payload(document_id, chunk_index=chunk_index, **kw),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Source Document API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceDocumentAPI:

    def test_create_source_returns_201(self, client: TestClient):
        """POST /api/books/{book_id}/sources returns 201 with document data."""
        book_id = _create_book(client, "Create Source Test")
        resp = client.post(f"/api/books/{book_id}/sources", json=_source_payload(book_id))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["book_id"] == book_id
        assert data["status"] == "created"

    def test_list_sources_returns_paginated_response(self, client: TestClient):
        """GET /api/books/{book_id}/sources returns paginated envelope."""
        book_id = _create_book(client, "List Sources Test")
        _create_source(client, book_id)
        resp = client.get(f"/api/books/{book_id}/sources")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_get_source_returns_source_detail(self, client: TestClient):
        """GET /api/books/{book_id}/sources/{document_id} returns full detail."""
        book_id = _create_book(client, "Get Source Test")
        doc = _create_source(client, book_id)
        resp = client.get(f"/api/books/{book_id}/sources/{doc['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == doc["id"]

    def test_patch_source_updates_source(self, client: TestClient):
        """PATCH /api/books/{book_id}/sources/{document_id} applies partial update."""
        book_id = _create_book(client, "Patch Source Test")
        doc = _create_source(client, book_id)
        resp = client.patch(
            f"/api/books/{book_id}/sources/{doc['id']}",
            json={"source_url": "https://example.com/paper.pdf"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["source_url"] == "https://example.com/paper.pdf"

    def test_delete_source_returns_success(self, client: TestClient):
        """DELETE /api/books/{book_id}/sources/{document_id} removes document."""
        book_id = _create_book(client, "Delete Source Test")
        doc = _create_source(client, book_id)
        resp = client.delete(f"/api/books/{book_id}/sources/{doc['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    def test_get_deleted_source_returns_404(self, client: TestClient):
        """After deletion, GET returns 404."""
        book_id = _create_book(client, "Deleted Source 404 Test")
        doc = _create_source(client, book_id)
        client.delete(f"/api/books/{book_id}/sources/{doc['id']}")
        resp = client.get(f"/api/books/{book_id}/sources/{doc['id']}")
        assert resp.status_code == 404

    def test_create_source_for_missing_book_returns_404(self, client: TestClient):
        """POST source for a non-existent book returns 404."""
        fake_id = str(uuid4())
        resp = client.post(f"/api/books/{fake_id}/sources", json=_source_payload(fake_id))
        assert resp.status_code == 404

    def test_patch_source_status_updates_status(self, client: TestClient):
        """PATCH /api/sources/{document_id}/status updates the document status."""
        book_id = _create_book(client, "Status Source Test")
        doc = _create_source(client, book_id)
        resp = client.patch(
            f"/api/sources/{doc['id']}/status",
            json={"status": "parsed"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "parsed"


# ══════════════════════════════════════════════════════════════════════════════
# Document Chunk API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentChunkAPI:

    def test_create_chunk_returns_201(self, client: TestClient):
        """POST /api/sources/{document_id}/chunks returns 201."""
        book_id = _create_book(client, "Create Chunk Test")
        doc = _create_source(client, book_id)
        resp = client.post(
            f"/api/sources/{doc['id']}/chunks",
            json=_chunk_payload(doc["id"], chunk_index=0),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["document_id"] == doc["id"]
        assert data["embedding_status"] == "pending"

    def test_list_chunks_returns_paginated_response(self, client: TestClient):
        """GET /api/sources/{document_id}/chunks returns paginated envelope."""
        book_id = _create_book(client, "List Chunks Test")
        doc = _create_source(client, book_id)
        _create_chunk(client, doc["id"], chunk_index=0)
        resp = client.get(f"/api/sources/{doc['id']}/chunks")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_get_chunk_returns_chunk_detail(self, client: TestClient):
        """GET /api/sources/{document_id}/chunks/{chunk_id} returns full detail."""
        book_id = _create_book(client, "Get Chunk Test")
        doc = _create_source(client, book_id)
        chunk = _create_chunk(client, doc["id"], chunk_index=0)
        resp = client.get(f"/api/sources/{doc['id']}/chunks/{chunk['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == chunk["id"]

    def test_patch_chunk_updates_chunk(self, client: TestClient):
        """PATCH /api/sources/{document_id}/chunks/{chunk_id} applies partial update."""
        book_id = _create_book(client, "Patch Chunk Test")
        doc = _create_source(client, book_id)
        chunk = _create_chunk(client, doc["id"], chunk_index=0)
        resp = client.patch(
            f"/api/sources/{doc['id']}/chunks/{chunk['id']}",
            json={"chunk_text": "Updated chunk content."},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["chunk_text"] == "Updated chunk content."

    def test_delete_chunk_returns_success(self, client: TestClient):
        """DELETE /api/sources/{document_id}/chunks/{chunk_id} deletes the chunk."""
        book_id = _create_book(client, "Delete Chunk Test")
        doc = _create_source(client, book_id)
        chunk = _create_chunk(client, doc["id"], chunk_index=0)
        resp = client.delete(f"/api/sources/{doc['id']}/chunks/{chunk['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    def test_create_chunk_for_missing_document_returns_404(self, client: TestClient):
        """POST chunk for a non-existent document returns 404."""
        fake_doc_id = str(uuid4())
        resp = client.post(
            f"/api/sources/{fake_doc_id}/chunks",
            json=_chunk_payload(fake_doc_id, chunk_index=0),
        )
        assert resp.status_code == 404

    def test_patch_chunk_embedding_status_updates_status_and_model(self, client: TestClient):
        """PATCH /api/chunks/{chunk_id}/embedding-status updates status + model."""
        book_id = _create_book(client, "Embedding Status Test")
        doc = _create_source(client, book_id)
        chunk = _create_chunk(client, doc["id"], chunk_index=0)
        resp = client.patch(
            f"/api/chunks/{chunk['id']}/embedding-status",
            json={"embedding_status": "completed", "embedding_model": "text-embedding-3-small"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["embedding_status"] == "completed"
        assert data["embedding_model"] == "text-embedding-3-small"

    def test_chunk_response_has_no_vector_field(self, client: TestClient):
        """DocumentChunkResponse must not expose a vector/embedding field."""
        book_id = _create_book(client, "No Vector Field Test")
        doc = _create_source(client, book_id)
        chunk = _create_chunk(client, doc["id"], chunk_index=0)
        resp = client.get(f"/api/sources/{doc['id']}/chunks/{chunk['id']}")
        data = resp.json()
        assert "embedding" not in data
        assert "vector" not in data


# ══════════════════════════════════════════════════════════════════════════════
# Chunking Endpoint Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestChunkingAPI:

    def test_chunk_endpoint_creates_chunks_from_raw_text(self, client: TestClient):
        """POST /api/sources/{document_id}/chunk creates chunks from raw_text."""
        book_id = _create_book(client, "Chunking Test Book")
        doc = _create_source(
            client, book_id,
            raw_text="This is a long document. " * 100,
        )
        resp = client.post(
            f"/api/sources/{doc['id']}/chunk",
            json={
                "document_id": doc["id"],
                "chunk_size": 200,
                "chunk_overlap": 20,
                "strategy": "fixed",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["chunks_created"] >= 1
        assert data["status"] == "completed"
        assert data["document_id"] == doc["id"]

    def test_chunk_endpoint_without_raw_text_returns_400(self, client: TestClient):
        """Chunking a document with no raw_text returns 400."""
        book_id = _create_book(client, "Empty Chunk Test")
        # Create doc with no raw_text
        resp = client.post(
            f"/api/books/{book_id}/sources",
            json={
                "book_id": book_id,
                "title": "Empty Doc",
                "source_type": "paper",
            },
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]
        resp = client.post(
            f"/api/sources/{doc_id}/chunk",
            json={
                "document_id": doc_id,
                "chunk_size": 500,
                "chunk_overlap": 50,
                "strategy": "fixed",
            },
        )
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Retrieval Endpoint Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrievalAPI:

    def _setup_chunks(self, client: TestClient, book_topic: str, texts: list[str]) -> str:
        """Helper: create book + source doc + chunks. Returns book_id."""
        book_id = _create_book(client, book_topic)
        combined = " ".join(texts)
        doc = _create_source(client, book_id, raw_text=combined)
        for idx, text in enumerate(texts):
            _create_chunk(client, doc["id"], chunk_index=idx, chunk_text=text)
        return book_id

    def test_retrieve_returns_lexical_matching_chunks(self, client: TestClient):
        """POST /api/rag/retrieve returns results for matching query."""
        book_id = self._setup_chunks(
            client,
            "Retrieve Lexical Test",
            ["neural networks are powerful", "python is easy to learn"],
        )
        resp = client.post(
            "/api/rag/retrieve",
            json={"query": "neural networks", "top_k": 5},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total_results"] >= 1
        assert any("neural" in r["chunk_text"].lower() for r in data["results"])

    def test_retrieve_respects_top_k(self, client: TestClient):
        """Retrieval does not return more results than top_k."""
        book_id = self._setup_chunks(
            client,
            "TopK Test",
            [f"machine learning concept {i}" for i in range(10)],
        )
        resp = client.post(
            "/api/rag/retrieve",
            json={"query": "machine learning", "top_k": 3},
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["results"]) <= 3

    def test_retrieve_filters_by_book_id(self, client: TestClient):
        """Retrieval with book_id only returns chunks from that book."""
        book_a = self._setup_chunks(client, "Book A Retrieve", ["alpha beta gamma"])
        book_b = self._setup_chunks(client, "Book B Retrieve", ["alpha delta epsilon"])

        resp = client.post(
            "/api/rag/retrieve",
            json={"query": "alpha", "top_k": 10, "book_id": book_b},
        )
        assert resp.status_code == 200, resp.text
        results = resp.json()["results"]
        for r in results:
            assert r["book_id"] == book_b

    def test_retrieve_does_not_require_embeddings(self, client: TestClient):
        """Retrieval endpoint works without any embedding data."""
        book_id = self._setup_chunks(client, "No Embedding Retrieve", ["test content for retrieval"])
        resp = client.post(
            "/api/rag/retrieve",
            json={"query": "test content", "top_k": 5},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Verify no raw vector field is returned in the response envelope
        # (The word 'vector' appears in the message string — check field names only)
        result_keys = set(data.keys())
        assert "embedding" not in result_keys
        assert data["status"] == "ok"
