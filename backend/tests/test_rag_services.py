"""
AIuthor Backend Tests — SourceDocumentService and DocumentChunkService unit tests.

Tests use a per-test transaction rollback for isolation against in-memory SQLite.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401

from app.services import (
    BookProjectService,
    SourceDocumentService,
    DocumentChunkService,
    NotFoundError,
    ConflictError,
    ValidationServiceError,
)
from app.schemas import (
    BookProjectCreate,
    SourceDocumentCreate,
    SourceDocumentUpdate,
    DocumentChunkCreate,
    DocumentChunkUpdate,
    ChunkingRequest,
)
from app.schemas.enums import TonePreset


# ── In-memory test engine ─────────────────────────────────────────────────────

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_ENGINE)
_Session = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    connection = _ENGINE.connect()
    transaction = connection.begin()
    session = _Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_book(db):
    return BookProjectService(db).create_book_project(
        BookProjectCreate(
            topic="AI Writing Assistant",
            reader_profile="Developers",
            genre="Technology",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=5,
        )
    )


def _source_create(book_id=None, **kw) -> SourceDocumentCreate:
    defaults = dict(
        book_id=book_id,
        title="ML Fundamentals Paper",
        source_type="paper",
        raw_text="Machine learning is a subset of artificial intelligence.",
    )
    defaults.update(kw)
    return SourceDocumentCreate(**defaults)


def _chunk_create(document_id, chunk_index=0, **kw) -> DocumentChunkCreate:
    defaults = dict(
        document_id=document_id,
        chunk_index=chunk_index,
        chunk_text="Machine learning is a subset of AI.",
    )
    defaults.update(kw)
    return DocumentChunkCreate(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# SourceDocumentService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceDocumentServiceCreate:

    def test_create_source_document_creates_for_book(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        doc = svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        assert doc.id is not None
        assert doc.book_id == book.id
        assert doc.status == "created"

    def test_create_source_document_for_missing_book_raises_not_found(self, db):
        from uuid import uuid4
        svc = SourceDocumentService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.create_source_document(_source_create(), book_id=uuid4())
        assert exc_info.value.code == "book_not_found"


class TestSourceDocumentServiceGet:

    def test_get_source_document_returns_document(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        created = svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        fetched = svc.get_source_document(created.id)
        assert fetched.id == created.id

    def test_get_source_document_missing_raises_not_found(self, db):
        from uuid import uuid4
        svc = SourceDocumentService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.get_source_document(uuid4())
        assert exc_info.value.code == "document_not_found"


class TestSourceDocumentServiceList:

    def test_list_source_documents_returns_items_and_total(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc.create_source_document(_source_create(book_id=book.id, title="Second"), book_id=book.id)
        items, total = svc.list_source_documents(book_id=book.id)
        assert total == 2
        assert len(items) == 2

    def test_list_source_documents_filters_by_status(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        doc = svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc.mark_document_status(doc.id, "parsed")
        svc.create_source_document(_source_create(book_id=book.id, title="Unparsed"), book_id=book.id)
        items, total = svc.list_source_documents(book_id=book.id, status="parsed")
        assert total == 1
        assert items[0].id == doc.id

    def test_list_source_documents_filters_by_source_type(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        svc.create_source_document(_source_create(book_id=book.id, source_type="paper"), book_id=book.id)
        svc.create_source_document(_source_create(book_id=book.id, source_type="web", title="Web Doc"), book_id=book.id)
        items, total = svc.list_source_documents(book_id=book.id, source_type="paper")
        assert total == 1
        assert items[0].source_type == "paper"

    def test_list_source_documents_search_finds_title(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        svc.create_source_document(_source_create(book_id=book.id, title="Deep Learning Guide"), book_id=book.id)
        svc.create_source_document(_source_create(book_id=book.id, title="Python Basics"), book_id=book.id)
        items, total = svc.list_source_documents(book_id=book.id, search="deep learning")
        assert total == 1
        assert "Deep Learning" in items[0].title


class TestSourceDocumentServiceUpdate:

    def test_update_source_document_updates_only_provided_fields(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        doc = svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        original_title = doc.title
        updated = svc.update_source_document(doc.id, SourceDocumentUpdate(source_url="https://example.com"))
        assert updated.source_url == "https://example.com"
        assert updated.title == original_title


class TestSourceDocumentServiceDelete:

    def test_delete_source_document_deletes_document(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        doc = svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        result = svc.delete_source_document(doc.id)
        assert result is True
        with pytest.raises(NotFoundError):
            svc.get_source_document(doc.id)


class TestSourceDocumentServiceStatus:

    def test_mark_document_status_updates_status(self, db):
        book = _make_book(db)
        svc = SourceDocumentService(db)
        doc = svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        updated = svc.mark_document_status(doc.id, "parsed")
        assert updated.status == "parsed"


# ══════════════════════════════════════════════════════════════════════════════
# DocumentChunkService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentChunkServiceCreate:

    def test_create_chunk_creates_chunk_for_document(self, db):
        book = _make_book(db)
        doc_svc = SourceDocumentService(db)
        doc = doc_svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        chunk = svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        assert chunk.id is not None
        assert chunk.document_id == doc.id
        assert chunk.embedding_status == "pending"

    def test_create_chunk_for_missing_document_raises_not_found(self, db):
        from uuid import uuid4
        svc = DocumentChunkService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.create_chunk(_chunk_create(uuid4(), chunk_index=0))
        assert exc_info.value.code == "document_not_found"

    def test_duplicate_chunk_index_raises_conflict(self, db):
        book = _make_book(db)
        doc_svc = SourceDocumentService(db)
        doc = doc_svc.create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        with pytest.raises(ConflictError) as exc_info:
            svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        assert exc_info.value.code == "duplicate_chunk_index"


class TestDocumentChunkServiceGet:

    def test_get_chunk_returns_chunk(self, db):
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        created = svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        fetched = svc.get_chunk(created.id)
        assert fetched.id == created.id

    def test_get_chunk_missing_raises_not_found(self, db):
        from uuid import uuid4
        svc = DocumentChunkService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.get_chunk(uuid4())
        assert exc_info.value.code == "chunk_not_found"


class TestDocumentChunkServiceList:

    def test_list_chunks_returns_items_and_total(self, db):
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        svc.create_chunk(_chunk_create(doc.id, chunk_index=1, chunk_text="Second chunk"), document_id=doc.id)
        items, total = svc.list_chunks(document_id=doc.id)
        assert total == 2
        assert len(items) == 2

    def test_list_chunks_filters_by_embedding_status(self, db):
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        ch = svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        svc.mark_embedding_status(ch.id, "completed", "text-embedding-3-small")
        svc.create_chunk(_chunk_create(doc.id, chunk_index=1, chunk_text="Second"), document_id=doc.id)
        items, total = svc.list_chunks(document_id=doc.id, embedding_status="completed")
        assert total == 1
        assert items[0].id == ch.id


class TestDocumentChunkServiceUpdate:

    def test_update_chunk_updates_chunk_text(self, db):
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        chunk = svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        updated = svc.update_chunk(chunk.id, DocumentChunkUpdate(chunk_text="Updated text"))
        assert updated.chunk_text == "Updated text"


class TestDocumentChunkServiceDelete:

    def test_delete_chunk_deletes_chunk(self, db):
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        chunk = svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        result = svc.delete_chunk(chunk.id)
        assert result is True
        with pytest.raises(NotFoundError):
            svc.get_chunk(chunk.id)


class TestDocumentChunkServiceEmbeddingStatus:

    def test_mark_embedding_status_updates_status_and_model(self, db):
        """mark_embedding_status changes status and model without storing a vector."""
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(_source_create(book_id=book.id), book_id=book.id)
        svc = DocumentChunkService(db)
        chunk = svc.create_chunk(_chunk_create(doc.id, chunk_index=0), document_id=doc.id)
        assert chunk.embedding_status == "pending"
        updated = svc.mark_embedding_status(chunk.id, "completed", "text-embedding-3-small")
        assert updated.embedding_status == "completed"
        assert updated.embedding_model == "text-embedding-3-small"
        # Module 6.0B added the embedding column to DocumentChunk.
        # mark_embedding_status must NOT write a vector — embedding stays None.
        assert hasattr(updated, "embedding"), "embedding attribute should exist (Module 6.0B)"
        assert updated.embedding is None, "mark_embedding_status must not store a vector"


class TestDocumentChunkServiceChunking:

    def test_simple_chunk_document_text_creates_chunks(self, db):
        """simple_chunk_document_text splits raw_text and stores chunks."""
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(
            _source_create(
                book_id=book.id,
                raw_text="Word " * 500,   # 500 words of content
            ),
            book_id=book.id,
        )
        svc = DocumentChunkService(db)
        resp = svc.simple_chunk_document_text(
            doc.id,
            ChunkingRequest(document_id=doc.id, chunk_size=200, chunk_overlap=20),
        )
        assert resp.chunks_created >= 1
        assert resp.status == "completed"
        assert resp.document_id == doc.id

        # Verify chunks were actually persisted
        items, total = svc.list_chunks(document_id=doc.id)
        assert total == resp.chunks_created

    def test_simple_chunk_with_empty_raw_text_raises_validation_error(self, db):
        """Empty raw_text raises ValidationServiceError."""
        book = _make_book(db)
        doc = SourceDocumentService(db).create_source_document(
            _source_create(book_id=book.id, raw_text=None),
            book_id=book.id,
        )
        svc = DocumentChunkService(db)
        with pytest.raises(ValidationServiceError) as exc_info:
            svc.simple_chunk_document_text(
                doc.id,
                ChunkingRequest(document_id=doc.id, chunk_size=500, chunk_overlap=50),
            )
        assert exc_info.value.code == "empty_raw_text"
