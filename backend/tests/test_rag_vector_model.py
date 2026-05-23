"""
AIuthor Backend — Tests: RAG Vector Model (Module 6.0B).

Tests for DocumentChunk vector fields and schema safety.
"""
from __future__ import annotations

import uuid

import pytest


class TestDocumentChunkVectorFields:
    """Tests that the DocumentChunk ORM model has all the vector columns."""

    def test_model_has_embedding_attribute(self):
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding")

    def test_model_has_embedding_provider(self):
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding_provider")

    def test_model_has_embedding_dimensions(self):
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding_dimensions")

    def test_model_has_embedding_created_at(self):
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding_created_at")

    def test_model_has_embedding_error(self):
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding_error")

    def test_model_has_embedding_model(self):
        """Pre-existing field must not have been removed."""
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding_model")

    def test_model_has_embedding_status(self):
        """Pre-existing field must not have been removed."""
        from app.models.document import DocumentChunk
        assert hasattr(DocumentChunk, "embedding_status")

    def test_chunk_in_sqlite_accepts_embedding_list(self, db):
        """DocumentChunk can be created in the SQLite test DB with a JSON embedding."""
        from app.models.document import SourceDocument, DocumentChunk
        from app.models.book import BookProject

        # Create a minimal book
        book = BookProject(
            topic="Vector Test Book",
            reader_profile="adults",
            genre="test",
            tone="neutral",
            target_chapters=1,
        )
        db.add(book)
        db.flush()

        doc = SourceDocument(
            book_id=book.id,
            title="Test Doc",
            source_type="test",
        )
        db.add(doc)
        db.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            book_id=book.id,
            chunk_index=0,
            chunk_text="Hello world chunk.",
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            embedding_status="completed",
            embedding_provider="mock",
            embedding_model="mock-embedding",
            embedding_dimensions=8,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        assert chunk.id is not None
        assert isinstance(chunk.embedding, list)
        assert len(chunk.embedding) == 8
        assert chunk.embedding_provider == "mock"
        assert chunk.embedding_dimensions == 8

    def test_chunk_embedding_is_none_by_default(self, db):
        """New chunks start with embedding=None."""
        from app.models.document import SourceDocument, DocumentChunk
        from app.models.book import BookProject

        book = BookProject(
            topic="Default Embed Book",
            reader_profile="adults",
            genre="test",
            tone="neutral",
            target_chapters=1,
        )
        db.add(book)
        db.flush()

        doc = SourceDocument(book_id=book.id, title="Doc", source_type="test")
        db.add(doc)
        db.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            book_id=book.id,
            chunk_index=0,
            chunk_text="No embedding yet.",
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)

        assert chunk.embedding is None
        assert chunk.embedding_status == "pending"

    def test_response_schema_does_not_expose_embedding(self):
        """DocumentChunkResponse schema must NOT have an 'embedding' field."""
        from app.schemas.rag import DocumentChunkResponse
        fields = DocumentChunkResponse.model_fields
        assert "embedding" not in fields, (
            "DocumentChunkResponse exposes raw embedding vector — this should be internal only."
        )

    def test_chunk_list_item_does_not_expose_embedding(self):
        """DocumentChunkListItem must NOT have an 'embedding' field."""
        from app.schemas.rag import DocumentChunkListItem
        fields = DocumentChunkListItem.model_fields
        assert "embedding" not in fields


class TestNewSchemasExist:
    """Tests that all 6 new schemas from Module 6.0B are importable and valid."""

    def test_chunk_embedding_request_importable(self):
        from app.schemas.rag import ChunkEmbeddingRequest
        req = ChunkEmbeddingRequest()
        assert req.force is False
        assert req.provider is None

    def test_bulk_embedding_request_importable(self):
        from app.schemas.rag import BulkChunkEmbeddingRequest
        req = BulkChunkEmbeddingRequest()
        assert req.force is False

    def test_bulk_embedding_request_validates_batch_size(self):
        from pydantic import ValidationError
        from app.schemas.rag import BulkChunkEmbeddingRequest
        with pytest.raises(ValidationError):
            BulkChunkEmbeddingRequest(batch_size=0)

    def test_semantic_retrieval_request_importable(self):
        from app.schemas.rag import SemanticRetrievalRequest
        req = SemanticRetrievalRequest(query="Test query.")
        assert req.top_k == 5
        assert req.include_raw_text is True

    def test_semantic_retrieval_request_rejects_empty_query(self):
        from pydantic import ValidationError
        from app.schemas.rag import SemanticRetrievalRequest
        with pytest.raises(ValidationError):
            SemanticRetrievalRequest(query="")

    def test_semantic_retrieval_request_validates_top_k(self):
        from pydantic import ValidationError
        from app.schemas.rag import SemanticRetrievalRequest
        with pytest.raises(ValidationError):
            SemanticRetrievalRequest(query="Test.", top_k=25)

    def test_semantic_retrieval_response_importable(self):
        from app.schemas.rag import SemanticRetrievalResponse, RetrievalResultItem
        resp = SemanticRetrievalResponse(
            query="q",
            provider="mock",
            model="mock-embedding",
            dimensions=8,
            results=[],
        )
        assert resp.pgvector_used is False
        assert resp.retrieval_mode == "semantic"
