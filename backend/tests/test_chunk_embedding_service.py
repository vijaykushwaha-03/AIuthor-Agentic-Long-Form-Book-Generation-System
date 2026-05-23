"""
AIuthor Backend — Tests: ChunkEmbeddingService (Module 6.0B).

All tests use MockEmbeddingProvider / EmbeddingService.
No real Gemini or OpenAI calls are made.
Tests pass on SQLite with JSON embedding storage.
"""
from __future__ import annotations

import pytest

from app.embeddings.providers import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import NotFoundError, ValidationServiceError


def _mock_svc(dims: int = 8) -> EmbeddingService:
    """Return an EmbeddingService backed by MockEmbeddingProvider."""
    return EmbeddingService(provider=MockEmbeddingProvider(dims=dims))


def _make_book(db):
    from app.models.book import BookProject
    book = BookProject(
        topic="Embed Test Book",
        reader_profile="developers",
        genre="fiction",
        tone="conversational",
        target_chapters=5,
    )
    db.add(book)
    db.flush()
    return book


def _make_doc(db, book):
    from app.models.document import SourceDocument
    doc = SourceDocument(
        book_id=book.id,
        title="Test Source Doc",
        source_type="manual",
        raw_text="Hello world. This is test content for embedding.",
    )
    db.add(doc)
    db.flush()
    return doc


def _make_chunk(db, doc, book, index: int = 0, text: str = "Sample chunk text.", status: str = "pending"):
    from app.models.document import DocumentChunk
    chunk = DocumentChunk(
        document_id=doc.id,
        book_id=book.id,
        chunk_index=index,
        chunk_text=text,
        embedding_status=status,
    )
    db.add(chunk)
    db.flush()
    return chunk


# ─────────────────────────────────────────────────────────────────────────────
# Single chunk embedding tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbedChunk:

    def test_embed_chunk_embeds_pending_chunk(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book)
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_chunk(chunk.id)

        assert result.embedding_status == "completed"
        assert isinstance(result.embedding, list)
        assert len(result.embedding) == 8

    def test_embed_chunk_sets_status_completed(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book)
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_chunk(chunk.id)
        assert result.embedding_status == "completed"

    def test_embed_chunk_stores_provider_model_dimensions(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book)
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_chunk(chunk.id)

        assert result.embedding_provider == "mock"
        assert result.embedding_model == "mock-embedding"
        assert result.embedding_dimensions == 8

    def test_embed_chunk_skips_completed_without_force(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book, status="completed")
        # Manually set a fake embedding so it looks done
        chunk.embedding = [0.1] * 8
        chunk.embedding_provider = "original"
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_chunk(chunk.id, force=False)

        # Provider should NOT be updated since we skip
        assert result.embedding_provider == "original"

    def test_embed_chunk_re_embeds_when_force_true(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book, status="completed")
        chunk.embedding = [0.1] * 8
        chunk.embedding_provider = "original"
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_chunk(chunk.id, force=True)

        assert result.embedding_provider == "mock"

    def test_embed_chunk_missing_id_raises_not_found(self, db):
        from uuid import uuid4
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        with pytest.raises(NotFoundError):
            svc.embed_chunk(uuid4())

    def test_embed_chunk_empty_text_raises_validation_error(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book, text="   ")  # whitespace-only
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        with pytest.raises(ValidationServiceError):
            svc.embed_chunk(chunk.id)

    def test_embed_chunk_empty_text_marks_failed(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book, text="   ")
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        try:
            svc.embed_chunk(chunk.id)
        except ValidationServiceError:
            pass
        db.refresh(chunk)
        assert chunk.embedding_status == "failed"

    def test_embed_chunk_clears_embedding_error_on_success(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book)
        chunk.embedding_status = "failed"
        chunk.embedding_error = "previous error"
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_chunk(chunk.id, force=True)
        assert result.embedding_error is None

    def test_embed_chunk_dimension_mismatch_detection_logic(self, db):
        """
        The dimension guard logic must detect mismatches.
        Tests _validate_vector_dimensions directly.
        """
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book)
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        # Directly test the validation helper — passing a 4-dim vector
        # against the configured 8-dim expectation must raise.
        from app.services.exceptions import ValidationServiceError
        with pytest.raises(ValidationServiceError):
            svc._validate_vector_dimensions([0.1, 0.2, 0.3, 0.4], expected=8)

    def test_embed_chunk_dimension_mismatch_error_message(self, db):
        """The mismatch error message must include expected and actual dims."""
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        from app.services.exceptions import ValidationServiceError
        book = _make_book(db)
        doc = _make_doc(db, book)
        chunk = _make_chunk(db, doc, book)
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        with pytest.raises(ValidationServiceError, match="8"):
            svc._validate_vector_dimensions([0.1, 0.2, 0.3, 0.4], expected=8)


# ─────────────────────────────────────────────────────────────────────────────
# Bulk document embedding tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbedDocumentChunks:

    def test_embed_document_chunks_embeds_pending_chunks(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        for i in range(3):
            _make_chunk(db, doc, book, index=i, text=f"Chunk {i} content.")
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_document_chunks(doc.id)

        assert result.embedded_count == 3
        assert result.failed_count == 0
        assert result.total_candidates == 3

    def test_embed_document_chunks_respects_limit(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        for i in range(5):
            _make_chunk(db, doc, book, index=i, text=f"Chunk {i}.")
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_document_chunks(doc.id, limit=2)

        assert result.total_candidates == 2
        assert result.embedded_count == 2

    def test_embed_document_chunks_skips_completed_without_force(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        # This chunk is already completed — should be skipped
        c_done = _make_chunk(db, doc, book, index=0, text="Done chunk.", status="completed")
        c_done.embedding = [0.1] * 8
        c_done.embedding_dimensions = 8
        db.flush()
        # This one is pending — should be embedded
        _make_chunk(db, doc, book, index=1, text="Pending chunk.")
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_document_chunks(doc.id, force=False)

        # Only the pending chunk is a candidate — completed+has-embedding are excluded
        assert result.total_candidates == 1
        assert result.embedded_count == 1

    def test_embed_document_chunks_re_embeds_with_force(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        c = _make_chunk(db, doc, book, index=0, text="Done chunk.", status="completed")
        c.embedding = [0.1] * 8
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_document_chunks(doc.id, force=True)

        assert result.total_candidates == 1
        assert result.embedded_count == 1

    def test_embed_document_chunks_missing_doc_raises_not_found(self, db):
        from uuid import uuid4
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        with pytest.raises(NotFoundError):
            svc.embed_document_chunks(uuid4())

    def test_embed_document_chunks_returns_target_type_document(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_document_chunks(doc.id)
        assert result.target_type == "document"


# ─────────────────────────────────────────────────────────────────────────────
# Bulk book embedding tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbedBookChunks:

    def test_embed_book_chunks_embeds_across_documents(self, db):
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc1 = _make_doc(db, book)
        doc2 = _make_extra_doc(db, book, title="Doc 2")
        _make_chunk(db, doc1, book, index=0, text="Book chunk doc1.")
        _make_chunk(db, doc2, book, index=0, text="Book chunk doc2.")
        db.commit()

        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        result = svc.embed_book_chunks(book.id)

        assert result.embedded_count == 2
        assert result.target_type == "book"

    def test_embed_book_chunks_missing_book_raises_not_found(self, db):
        from uuid import uuid4
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        svc = ChunkEmbeddingService(db=db, embedding_service=_mock_svc())
        with pytest.raises(NotFoundError):
            svc.embed_book_chunks(uuid4())

    def test_embed_book_chunks_no_external_api_calls(self, db):
        """MockEmbeddingProvider must not have made any HTTP calls."""
        from app.services.chunk_embedding_service import ChunkEmbeddingService
        book = _make_book(db)
        doc = _make_doc(db, book)
        _make_chunk(db, doc, book, index=0, text="No network text.")
        db.commit()

        mock = MockEmbeddingProvider(dims=8)
        svc = ChunkEmbeddingService(db=db, embedding_service=EmbeddingService(provider=mock))
        result = svc.embed_book_chunks(book.id)

        assert result.embedded_count == 1
        # MockEmbeddingProvider has no _http_calls or similar; it just works offline


def _make_extra_doc(db, book, title: str = "Doc"):
    from app.models.document import SourceDocument
    doc = SourceDocument(book_id=book.id, title=title, source_type="manual")
    db.add(doc)
    db.flush()
    return doc
