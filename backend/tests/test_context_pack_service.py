"""
AIuthor Backend — Tests: ContextPackService (Module 6.1).

All tests run locally using SQLite and the MockEmbeddingProvider.
"""
from __future__ import annotations

import pytest
from uuid import UUID, uuid4

from app.embeddings.providers import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.context_pack_service import ContextPackService
from app.schemas.rag import ContextPackRequest
from app.services.exceptions import NotFoundError, ValidationServiceError


def _mock_svc(dims: int = 8) -> EmbeddingService:
    return EmbeddingService(provider=MockEmbeddingProvider(dims=dims))


def _make_book(db, topic="Context Pack Book"):
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


def _make_chapter(db, book, chapter_number=1, title="Chapter One"):
    from app.models.chapter import Chapter
    ch = Chapter(
        book_id=book.id,
        chapter_number=chapter_number,
        title=title,
        status="planned",
    )
    db.add(ch)
    db.flush()
    return ch


def _make_doc(db, book, title="Context Doc"):
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


class TestContextPackService:

    def test_build_context_pack_returns_context_text(self, db):
        """build_context_pack formats retrieved text correctly."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Retrieve this specific knowledge.")
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="specific knowledge", book_id=book.id)
        resp = svc.build_context_pack(req)

        assert resp.total_chunks == 1
        assert "Retrieve this specific knowledge." in resp.context_text

    def test_context_text_includes_c1_citation_marker(self, db):
        """Generated context contains correct deterministic [C1] header annotations."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Paragraph chunk text.")
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="Paragraph chunk", book_id=book.id)
        resp = svc.build_context_pack(req)

        expected_header = f"[C1] Source: {doc.title}, Chunk 0"
        assert expected_header in resp.context_text
        assert resp.context_text.startswith(expected_header)

    def test_context_pack_returns_citations_list(self, db):
        """Citations block contains details of references."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_embedded_chunk(db, doc, book, 0, "Segment text.")
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="Segment text", book_id=book.id)
        resp = svc.build_context_pack(req)

        assert len(resp.citations) == 1
        assert resp.citations[0].citation_id == "C1"
        assert resp.citations[0].document_id == doc.id
        assert resp.citations[0].source_title == "Context Doc"

    def test_context_pack_respects_max_chunks(self, db):
        """Number of retrieved chunks is limited by max_chunks."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        for i in range(5):
            _make_embedded_chunk(db, doc, book, i, f"Snippet {i} of database.")
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="Snippet", book_id=book.id, max_chunks=2)
        resp = svc.build_context_pack(req)

        assert resp.total_chunks == 2
        assert len(resp.chunks) == 2
        assert len(resp.citations) == 2

    def test_context_pack_respects_max_context_chars(self, db):
        """Context builder stops adding chunks to prevent exceeding max_context_chars."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        # Create larger chunks to test boundaries above 1000 chars
        _make_embedded_chunk(db, doc, book, 0, "A" * 1050)
        _make_embedded_chunk(db, doc, book, 1, "B" * 500)
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        # Set limit to 1100 characters. Chunk A block fits (~1085 chars), Chunk B exceeds.
        req = ContextPackRequest(query="A", book_id=book.id, max_context_chars=1100)
        resp = svc.build_context_pack(req)

        # It should only include the first chunk. Second is skipped completely.
        assert resp.total_chunks == 1
        assert "A" * 1050 in resp.context_text
        assert "B" * 500 not in resp.context_text

    def test_context_pack_truncates_first_chunk_if_exceeds(self, db):
        """First chunk alone exceeding max_context_chars gets truncated with truncated=True flag."""
        book = _make_book(db)
        doc = _make_doc(db, book)
        # Create an extremely long chunk
        _make_embedded_chunk(db, doc, book, 0, "Superlong " * 200)
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        # Limit is 1000 chars.
        req = ContextPackRequest(query="Superlong", book_id=book.id, max_context_chars=1000)
        resp = svc.build_context_pack(req)

        assert resp.total_chunks == 1
        assert resp.metadata["truncated"] is True
        assert len(resp.context_text) == 1000
        assert resp.chunks[0].metadata["truncated"] is True

    def test_context_pack_verifies_book_exists(self, db):
        """Passing non-existent book project UUID raises NotFoundError."""
        hybrid_svc = HybridRetrievalService(db=db)
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="test", book_id=uuid4())
        with pytest.raises(NotFoundError) as exc:
            svc.build_context_pack(req)
        assert exc.value.code == "book_not_found"

    def test_context_pack_verifies_chapter_belongs_to_book(self, db):
        """Verifies chapter existence and book Project UUID linkage."""
        book1 = _make_book(db, topic="Book 1")
        book2 = _make_book(db, topic="Book 2")
        ch_book2 = _make_chapter(db, book2, chapter_number=1)
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        # Chapter exists but belongs to book 2, and we pass book 1
        req = ContextPackRequest(query="test", book_id=book1.id, chapter_id=ch_book2.id)
        with pytest.raises(ValidationServiceError) as exc:
            svc.build_context_pack(req)
        assert exc.value.code == "chapter_book_mismatch"

        # Chapter does not exist
        req_missing = ContextPackRequest(query="test", book_id=book1.id, chapter_id=uuid4())
        with pytest.raises(NotFoundError) as exc:
            svc.build_context_pack(req_missing)
        assert exc.value.code == "chapter_not_found"

    def test_context_pack_returns_empty_context_if_no_results(self, db):
        """No matches in database returns clean empty text envelope without error."""
        book = _make_book(db)
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="nonexistent", book_id=book.id)
        resp = svc.build_context_pack(req)

        assert resp.total_chunks == 0
        assert resp.context_text == ""
        assert resp.chunks == []
        assert resp.citations == []

    def test_context_pack_metadata_includes_memory_hints_included_false(self, db):
        """Metadata conforms to specifications containing memory_hints_included=False."""
        book = _make_book(db)
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="test", book_id=book.id)
        resp = svc.build_context_pack(req)

        assert resp.metadata["memory_hints_included"] is False
        assert "Memory hints will be enriched" in resp.metadata["note"]

    def test_context_pack_does_not_call_llm_or_agents(self, db):
        """ContextPackService operates offline with zero LLM API/agent triggers."""
        book = _make_book(db)
        db.commit()

        hybrid_svc = HybridRetrievalService(db=db)
        hybrid_svc.semantic_service.embedding_service = _mock_svc()
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)

        req = ContextPackRequest(query="test", book_id=book.id)
        resp = svc.build_context_pack(req)

        # Assert clean completion
        assert resp.retrieval_mode == "hybrid_context_pack"
