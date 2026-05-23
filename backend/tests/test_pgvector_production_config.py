from __future__ import annotations

import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.pgvector_check import is_pgvector_available, assert_pgvector_ready
from app.models.document import DocumentChunk, SourceDocument
from app.schemas.rag import DocumentChunkResponse
from app.services.exceptions import ServiceError
from app.services.semantic_retrieval_service import SemanticRetrievalService


def test_sqlite_fallback_remains_allowed_in_tests():
    """Verify that SQLite tests do not fail on missing pgvector."""
    # Setup test in-memory SQLite DB
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    with Session() as session:
        # Check pgvector check works
        assert not is_pgvector_available(session)
        # assert_pgvector_ready should be a no-op on SQLite
        assert_pgvector_ready(session)


def test_pgvector_readiness_utility_returns_false_on_sqlite():
    """Verify is_pgvector_available returns False on SQLite."""
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    with Session() as session:
        assert is_pgvector_available(session) is False


def test_config_has_defaults():
    """Verify configuration defaults for RAG vector dimensions and fallback settings."""
    from app.config import Settings
    
    assert "RAG_VECTOR_DIMENSIONS" in Settings.model_fields
    assert Settings.model_fields["RAG_VECTOR_DIMENSIONS"].default == 768
    
    assert "ALLOW_PGVECTOR_FALLBACK" in Settings.model_fields
    # Default should be False as required in Part 7
    assert Settings.model_fields["ALLOW_PGVECTOR_FALLBACK"].default is False


def test_check_pgvector_embedding_script_importable():
    """Verify the check_pgvector_embedding script can be imported without running."""
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts"))
    sys.path.insert(0, script_dir)
    try:
        import check_pgvector_embedding
        assert check_pgvector_embedding.main is not None
    finally:
        if "check_pgvector_embedding" in sys.modules:
            del sys.modules["check_pgvector_embedding"]
        sys.path.remove(script_dir)


def test_document_chunk_model_has_embedding_column():
    """Verify DocumentChunk has an embedding column in SQLAlchemy model."""
    assert hasattr(DocumentChunk, "embedding")
    col = DocumentChunk.__table__.columns.get("embedding")
    assert col is not None
    # Verify metadata columns exist on model
    for col_name in [
        "embedding_dimensions",
        "embedding_provider",
        "embedding_created_at",
        "embedding_error"
    ]:
        assert hasattr(DocumentChunk, col_name)


def test_response_schema_does_not_expose_raw_embedding():
    """Verify that DocumentChunkResponse schema does not expose the embedding field."""
    fields = DocumentChunkResponse.model_fields
    assert "embedding" not in fields


def test_pgvector_assert_raises_on_postgres_if_missing():
    """Verify that assert_pgvector_ready raises ServiceError on mock PostgreSQL if extension is missing."""
    class MockDialect:
        name = "postgresql"
        
    class MockBind:
        dialect = MockDialect()
        
    class MockSession:
        bind = MockBind()
        
        def execute(self, *args, **kwargs):
            # Mock return that extension does not exist
            class MockResult:
                def fetchone(self):
                    return (False,)
            return MockResult()

    session = MockSession()
    with pytest.raises(ServiceError) as exc_info:
        assert_pgvector_ready(session)  # type: ignore
    assert "pgvector extension 'vector' is not enabled" in str(exc_info.value)
