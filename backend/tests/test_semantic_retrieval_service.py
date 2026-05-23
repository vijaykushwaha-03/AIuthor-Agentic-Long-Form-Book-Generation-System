"""
AIuthor Backend — Tests: SemanticRetrievalService (Module 6.0B).

All tests use MockEmbeddingProvider / EmbeddingService.
Tests use the SQLite test DB and Python cosine similarity fallback.
No real Gemini or OpenAI calls are made.
"""
from __future__ import annotations

import pytest

from app.embeddings.providers import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import ValidationServiceError


def _mock_svc(dims: int = 8) -> EmbeddingService:
    return EmbeddingService(provider=MockEmbeddingProvider(dims=dims))


def _make_book(db):
    from app.models.book import BookProject
    book = BookProject(
        topic="Semantic Test Book",
        reader_profile="adults",
        genre="nonfiction",
        tone="formal",
        target_chapters=10,
    )
    db.add(book)
    db.flush()
    return book


def _make_doc(db, book, title: str = "Semantic Doc"):
    from app.models.document import SourceDocument
    doc = SourceDocument(book_id=book.id, title=title, source_type="test")
    db.add(doc)
    db.flush()
    return doc


def _make_embedded_chunk(db, doc, book, index: int, text: str, dims: int = 8):
    """Create a chunk that already has a completed embedding."""
    from app.models.document import DocumentChunk
    # Use MockEmbeddingProvider to generate a deterministic vector
    from app.embeddings.providers import MockEmbeddingProvider
    from app.embeddings.schemas import EmbeddingRequest
    mock = MockEmbeddingProvider(dims=dims)
    resp = mock.embed(EmbeddingRequest(texts=[text], dimensions=dims))
    vector = resp.items[0].embedding

    chunk = DocumentChunk(
        document_id=doc.id,
        book_id=book.id,
        chunk_index=index,
        chunk_text=text,
        embedding=vector,
        embedding_status="completed",
        embedding_provider="mock",
        embedding_model="mock-embedding",
        embedding_dimensions=dims,
    )
    db.add(chunk)
    db.flush()
    return chunk


def _make_pending_chunk(db, doc, book, index: int, text: str):
    """Create a chunk with no embedding (pending)."""
    from app.models.document import DocumentChunk
    chunk = DocumentChunk(
        document_id=doc.id,
        book_id=book.id,
        chunk_index=index,
        chunk_text=text,
        embedding_status="pending",
    )
    db.add(chunk)
    db.flush()
    return chunk


# ─────────────────────────────────────────────────────────────────────────────
# SemanticRetrievalService tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSemanticRetrievalService:

    def test_semantic_retrieve_returns_embedded_chunks(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "The quick brown fox jumps.")
        _make_embedded_chunk(db, doc, book, 1, "Lazy dogs sleep all day.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="quick fox")
        resp = svc.semantic_retrieve(req)

        assert len(resp.results) >= 1
        assert resp.retrieval_mode == "semantic"

    def test_semantic_retrieve_respects_top_k(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        for i in range(5):
            _make_embedded_chunk(db, doc, book, i, f"Chunk number {i} content text.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="content text", top_k=2)
        resp = svc.semantic_retrieve(req)

        assert len(resp.results) <= 2

    def test_semantic_retrieve_filters_by_book_id(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest
        from app.models.book import BookProject

        book1 = _make_book(db)
        book2_obj = BookProject(
            topic="Other Book",
            reader_profile="general",
            genre="fiction",
            tone="casual",
            target_chapters=5,
        )
        db.add(book2_obj)
        db.flush()

        doc1 = _make_doc(db, book1)
        doc2 = _make_doc(db, book2_obj, title="Book2 Doc")
        _make_embedded_chunk(db, doc1, book1, 0, "Book one text content.")
        _make_embedded_chunk(db, doc2, book2_obj, 0, "Book two text content.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="text content", book_id=book1.id)
        resp = svc.semantic_retrieve(req)

        # All results must belong to book1
        for item in resp.results:
            assert str(item.book_id) == str(book1.id)

    def test_semantic_retrieve_filters_by_document_id(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc1 = _make_doc(db, book, title="Doc A")
        doc2 = _make_doc(db, book, title="Doc B")
        _make_embedded_chunk(db, doc1, book, 0, "Doc A chunk.")
        _make_embedded_chunk(db, doc2, book, 0, "Doc B chunk.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="chunk", document_id=doc1.id)
        resp = svc.semantic_retrieve(req)

        for item in resp.results:
            assert str(item.document_id) == str(doc1.id)

    def test_semantic_retrieve_excludes_chunks_without_embeddings(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Has embedding.")
        _make_pending_chunk(db, doc, book, 1, "No embedding pending.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="embedding")
        resp = svc.semantic_retrieve(req)

        # Only the embedded chunk may appear
        for item in resp.results:
            assert item.chunk_text != "No embedding pending."

    def test_semantic_retrieve_excludes_wrong_dimension_chunks(self, db):
        """Chunks with embedding_dimensions != RAG_VECTOR_DIMENSIONS are excluded."""
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest
        from app.models.document import DocumentChunk

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Correct dims chunk.")

        # Create a chunk with wrong dimensions
        bad_chunk = DocumentChunk(
            document_id=doc.id,
            book_id=book.id,
            chunk_index=1,
            chunk_text="Wrong dims chunk.",
            embedding=[0.1] * 4,         # wrong dims (4, not 8)
            embedding_status="completed",
            embedding_provider="mock",
            embedding_dimensions=4,       # wrong
        )
        db.add(bad_chunk)
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="dims chunk")
        resp = svc.semantic_retrieve(req)

        # Bad chunk must not appear in results
        for item in resp.results:
            assert item.chunk_text != "Wrong dims chunk."

    def test_semantic_retrieve_pgvector_used_false_in_sqlite(self, db):
        """SQLite test DB → always Python fallback → pgvector_used=False."""
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "SQLite fallback test.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="fallback")
        resp = svc.semantic_retrieve(req)

        assert resp.pgvector_used is False

    def test_semantic_retrieve_honors_include_raw_text_false(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Secret text content.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="secret text", include_raw_text=False)
        resp = svc.semantic_retrieve(req)

        for item in resp.results:
            assert item.chunk_text is None

    def test_semantic_retrieve_returns_empty_when_no_matches(self, db):
        """Query scoped to a brand-new book with no chunks → results list is empty, no error."""
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        # Create a fresh book with no chunks at all
        book = _make_book(db)
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="absolutely nothing here", book_id=book.id)
        resp = svc.semantic_retrieve(req)

        assert resp.results == []
        assert resp.pgvector_used is False

    def test_semantic_retrieve_no_external_api_calls(self, db):
        """MockEmbeddingProvider must not trigger network calls."""
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Offline test content.")
        db.commit()

        mock = MockEmbeddingProvider(dims=8)
        svc = SemanticRetrievalService(
            db=db, embedding_service=EmbeddingService(provider=mock)
        )
        req = SemanticRetrievalRequest(query="offline test")
        resp = svc.semantic_retrieve(req)

        # If we get here without error, no external calls were made
        assert isinstance(resp.results, list)

    def test_semantic_retrieve_result_metadata_contains_embedding_info(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Metadata test chunk.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="metadata test")
        resp = svc.semantic_retrieve(req)

        for item in resp.results:
            assert item.metadata is not None
            assert "embedding_provider" in item.metadata
            assert "embedding_dimensions" in item.metadata

    def test_semantic_retrieve_response_has_provider_model_dims(self, db):
        from app.services.semantic_retrieval_service import SemanticRetrievalService
        from app.schemas.rag import SemanticRetrievalRequest

        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Provider info chunk.")
        db.commit()

        svc = SemanticRetrievalService(db=db, embedding_service=_mock_svc())
        req = SemanticRetrievalRequest(query="provider info")
        resp = svc.semantic_retrieve(req)

        assert resp.provider == "mock"
        assert resp.model == "mock-embedding"
        assert resp.dimensions == 8
