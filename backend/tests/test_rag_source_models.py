from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.book import BookProject
from app.models.document import SourceDocument, DocumentChunk


def test_base_metadata_contains_rag_tables():
    """Verify that RAG source tables are registered in SQLAlchemy metadata."""
    expected_tables = {"source_documents", "document_chunks"}
    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_rag_source_models_lifecycle():
    """Verify instantiation, relationships, cascades, and constraints on SQLite."""
    # Setup in-memory SQLite database for isolated unit test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. Instantiate BookProject
        project = BookProject(
            topic="Beginner Personal Finance Guide",
            reader_profile="Young adults aged 18-25 seeking basic budget tips",
            genre="Finance",
            tone="Conversational",
            target_chapters=10,
            words_per_chapter=2000,
            status="created",
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # 2. Instantiate SourceDocument
        doc = SourceDocument(
            book_id=project.id,
            title="Introduction to Compound Interest",
            source_type="uploaded_pdf",
            source_url="https://example.com/interest.pdf",
            raw_text="Compound interest is the interest on a loan or deposit...",
            document_metadata={"author": "John Doe"},
            status="created",
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        assert isinstance(doc.id, uuid.UUID)
        assert doc.book_id == project.id
        assert doc.title == "Introduction to Compound Interest"
        assert doc.source_type == "uploaded_pdf"
        assert doc.source_url == "https://example.com/interest.pdf"
        assert doc.status == "created"
        assert doc.book == project
        assert doc in project.source_documents
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)

        # 3. Instantiate DocumentChunk
        chunk = DocumentChunk(
            document_id=doc.id,
            book_id=project.id,
            chunk_index=0,
            chunk_text="Compound interest is the interest on a loan or deposit",
            token_count=10,
            chunk_metadata={"page": 1},
            embedding_model="text-embedding-3-small",
            embedding_status="pending",
        )
        session.add(chunk)
        session.commit()
        session.refresh(chunk)

        assert isinstance(chunk.id, uuid.UUID)
        assert chunk.document_id == doc.id
        assert chunk.book_id == project.id
        assert chunk.chunk_index == 0
        assert chunk.chunk_text == "Compound interest is the interest on a loan or deposit"
        assert chunk.token_count == 10
        assert chunk.embedding_status == "pending"
        assert chunk.document == doc
        assert chunk in doc.chunks
        assert chunk.book == project
        assert chunk in project.document_chunks
        assert isinstance(chunk.created_at, datetime)
        assert isinstance(chunk.updated_at, datetime)

        # 4. Verify unique constraint on (document_id, chunk_index)
        duplicate_chunk = DocumentChunk(
            document_id=doc.id,
            book_id=project.id,
            chunk_index=0,
            chunk_text="Another duplicate text",
        )
        session.add(duplicate_chunk)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 5. Check Cascade Deletes (Deleting book deletes documents & chunks)
        session.delete(project)
        session.commit()

        # Check cascading deletion
        assert session.query(SourceDocument).filter_by(book_id=project.id).count() == 0
        assert session.query(DocumentChunk).filter_by(book_id=project.id).count() == 0
