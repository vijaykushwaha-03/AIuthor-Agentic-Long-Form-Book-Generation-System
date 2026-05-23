"""
AIuthor Backend — Tests: HybridRetrievalService (Module 6.1).

All tests run locally using SQLite and the MockEmbeddingProvider.
"""
from __future__ import annotations

import pytest
from uuid import UUID, uuid4

from app.embeddings.providers import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.schemas.rag import HybridRetrievalRequest


def _mock_svc(dims: int = 8) -> EmbeddingService:
    return EmbeddingService(provider=MockEmbeddingProvider(dims=dims))


def _make_book(db, topic="Hybrid Book"):
    from app.models.book import BookProject
    book = BookProject(
        topic=topic,
        reader_profile="general",
        genre="nonfiction",
        tone="neutral",
        target_chapters=5,
    )
    db.add(book)
    db.flush()
    return book


def _make_doc(db, book, title="Hybrid Doc"):
    from app.models.document import SourceDocument
    doc = SourceDocument(book_id=book.id, title=title, source_type="test")
    db.add(doc)
    db.flush()
    return doc


def _make_embedded_chunk(db, doc, book, index: int, text: str, dims: int = 8):
    from app.models.document import DocumentChunk
    mock = MockEmbeddingProvider(dims=dims)
    resp = mock.embed(EmbeddingRequest_local(text, dims))
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


def EmbeddingRequest_local(text: str, dimensions: int = 8):
    from app.embeddings.schemas import EmbeddingRequest
    return EmbeddingRequest(texts=[text], dimensions=dimensions)


class TestHybridRetrievalService:

    def test_hybrid_retrieve_returns_results_from_semantic(self, db):
        """hybrid_retrieve successfully integrates vector search results."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "The quick brown fox jumps.")
        _make_embedded_chunk(db, doc, book, 1, "Lazy dogs sleep all day.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        # Inject embedding service in underlying semantic service
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="The quick brown fox jumps.", semantic_weight=1.0, lexical_weight=0.0)
        resp = svc.hybrid_retrieve(req)

        assert len(resp.results) >= 1
        assert resp.semantic_count > 0
        assert resp.results[0].chunk_text == "The quick brown fox jumps."

    def test_hybrid_retrieve_returns_results_from_lexical(self, db):
        """hybrid_retrieve successfully integrates keyword LIKE search results."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "The quick brown fox jumps.")
        _make_embedded_chunk(db, doc, book, 1, "Lazy dogs sleep all day.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        # Zero semantic weight, pure lexical keyword matching
        req = HybridRetrievalRequest(query="sleeping lazy dogs", semantic_weight=0.0, lexical_weight=1.0)
        resp = svc.hybrid_retrieve(req)

        assert len(resp.results) == 1
        assert resp.lexical_count + resp.merged_count == 1
        assert resp.results[0].chunk_text == "Lazy dogs sleep all day."

    def test_hybrid_retrieve_deduplicates_same_chunk(self, db):
        """Chunks matched by both semantic and lexical are merged into one item with 'hybrid' mode."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "The quick brown fox jumps over the lazy dog.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="lazy dog", semantic_weight=0.5, lexical_weight=0.5)
        resp = svc.hybrid_retrieve(req)

        # Chunks matched in both should only appear once
        assert len(resp.results) == 1
        assert resp.merged_count == 1
        assert resp.citations[0].retrieval_mode == "hybrid"

    def test_hybrid_retrieve_produces_combined_scores(self, db):
        """Scores are correctly calculated: sem_score * sem_weight + lex_score * lex_weight."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Match both methods here.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        # Get individual semantic score first
        req_sem = HybridRetrievalRequest(query="Match both methods here.", semantic_weight=1.0, lexical_weight=0.0)
        resp_sem = svc.hybrid_retrieve(req_sem)
        sem_score = resp_sem.results[0].score

        # Hybrid retrieve with semantic=0.6 and lexical=0.4
        # Lexical score for exact phrase is 1.0
        req_hyb = HybridRetrievalRequest(query="Match both methods here.", semantic_weight=0.6, lexical_weight=0.4)
        resp_hyb = svc.hybrid_retrieve(req_hyb)

        expected_score = sem_score * 0.6 + 1.0 * 0.4
        assert pytest.approx(resp_hyb.results[0].score, 0.0001) == expected_score

    def test_hybrid_retrieve_respects_top_k(self, db):
        """Results count is capped by top_k."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        for i in range(10):
            _make_embedded_chunk(db, doc, book, i, f"Topic paragraph matching index {i}")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="Topic paragraph", top_k=3)
        resp = svc.hybrid_retrieve(req)

        assert len(resp.results) == 3
        assert len(resp.citations) == 3

    def test_hybrid_retrieve_filters_by_book_id(self, db):
        """Scoping filters are correctly passed through and applied."""
        book1 = _make_book(db, topic="Book 1")
        book2 = _make_book(db, topic="Book 2")
        doc1 = _make_doc(db, book1)
        doc2 = _make_doc(db, book2)
        _make_embedded_chunk(db, doc1, book1, 0, "Target content inside Book 1")
        _make_embedded_chunk(db, doc2, book2, 0, "Target content inside Book 2")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="Target content", book_id=book1.id)
        resp = svc.hybrid_retrieve(req)

        # Chunks must only belong to book1
        assert len(resp.results) == 1
        assert resp.results[0].book_id == book1.id

    def test_hybrid_retrieve_filters_by_document_id(self, db):
        """Scoping filters by document_id are correctly applied."""
        book = _make_book(db)
        doc1 = _make_doc(db, book, title="Doc 1")
        doc2 = _make_doc(db, book, title="Doc 2")
        _make_embedded_chunk(db, doc1, book, 0, "Content in Doc 1")
        _make_embedded_chunk(db, doc2, book, 0, "Content in Doc 2")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="Content", document_id=doc1.id)
        resp = svc.hybrid_retrieve(req)

        assert len(resp.results) == 1
        assert resp.results[0].document_id == doc1.id

    def test_hybrid_retrieve_supports_min_score(self, db):
        """Chunks scoring below min_score are discarded."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "High relevance matching string.")
        _make_embedded_chunk(db, doc, book, 1, "Low relevance garbage.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        # Let's request lexical only to control scores easily
        # "garbage collector bin" query matching chunk 1 gives 1/3 score = 0.33
        req = HybridRetrievalRequest(
            query="garbage collector bin",
            semantic_weight=0.0,
            lexical_weight=1.0,
            min_score=0.5,
        )
        resp = svc.hybrid_retrieve(req)

        # The 0.33 matches are excluded by min_score=0.5
        assert len(resp.results) == 0

    def test_hybrid_retrieve_builds_citations_c1_c2(self, db):
        """Citation list returns ordered C1, C2 etc sequential response-local IDs."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "First chunk text.")
        _make_embedded_chunk(db, doc, book, 1, "Second chunk text.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="chunk text")
        resp = svc.hybrid_retrieve(req)

        assert len(resp.citations) == 2
        assert resp.citations[0].citation_id == "C1"
        assert resp.citations[1].citation_id == "C2"
        assert resp.citations[0].source_title == "Hybrid Doc"

    def test_lexical_retrieve_chunks_scores_exact_phrase_higher(self, db):
        """Exact phrase match = 1.0, word overlap = count / total_terms."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "The lazy dogs sleep.")
        _make_embedded_chunk(db, doc, book, 1, "Dogs sleep and run around.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        results = svc.lexical_retrieve_chunks(query="lazy dogs sleep")

        assert len(results) == 2
        # First chunk contains exact phrase "lazy dogs sleep" -> score = 1.0
        assert results[0]["chunk"].chunk_index == 0
        assert results[0]["score"] == 1.0

        # Second chunk matches only terms "dogs" and "sleep" -> 2 out of 3 terms -> score = 0.666
        assert results[1]["chunk"].chunk_index == 1
        assert pytest.approx(results[1]["score"], 0.001) == 2 / 3

    def test_lexical_retrieve_chunks_returns_empty_list_for_no_match(self, db):
        """Returns empty list cleanly when no terms are matched in database."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Just simple content.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        results = svc.lexical_retrieve_chunks(query="unmatched queries")
        assert results == []

    def test_hybrid_retrieve_does_not_expose_embeddings(self, db):
        """Verifies that retrieval responses do not leak embedding floats."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Hide raw embeddings.")
        db.commit()

        svc = HybridRetrievalService(db=db)
        svc.semantic_service.embedding_service = _mock_svc()

        req = HybridRetrievalRequest(query="embeddings")
        resp = svc.hybrid_retrieve(req)

        assert len(resp.results) == 1
        # Assert neither Pydantic schema nor result item dictionary has raw embedding list
        assert not hasattr(resp.results[0], "embedding")
        assert "embedding" not in resp.results[0].model_dump()
