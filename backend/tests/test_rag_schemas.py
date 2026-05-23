from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from app.schemas import (
    SourceDocumentCreate,
    SourceDocumentUpdate,
    SourceDocumentResponse,
    SourceDocumentListItem,
    DocumentChunkCreate,
    DocumentChunkUpdate,
    DocumentChunkResponse,
    DocumentChunkListItem,
    ChunkingRequest,
    ChunkingResponse,
    RetrievalRequest,
    RetrievalResultItem,
    RetrievalResponse,
)


def test_package_exports_rag():
    """19. Verify all new RAG schemas are properly exported from the package."""
    assert SourceDocumentCreate is not None
    assert SourceDocumentUpdate is not None
    assert SourceDocumentResponse is not None
    assert SourceDocumentListItem is not None
    assert DocumentChunkCreate is not None
    assert DocumentChunkUpdate is not None
    assert DocumentChunkResponse is not None
    assert DocumentChunkListItem is not None
    assert ChunkingRequest is not None
    assert ChunkingResponse is not None
    assert RetrievalRequest is not None
    assert RetrievalResultItem is not None
    assert RetrievalResponse is not None


# ── SourceDocumentCreate Tests ───────────────────────────────────────────────

def test_source_document_create_valid():
    """1. Valid data passes validation for SourceDocumentCreate."""
    schema = SourceDocumentCreate(
        title="Income Statement Guide",
        source_type="pdf",
        source_url="https://example.com/guide.pdf",
        raw_text="This is the raw content of the guide.",
        document_metadata={"author": "Finance Corp"}
    )
    assert schema.title == "Income Statement Guide"
    assert schema.source_type == "pdf"
    assert schema.status == "created"


def test_source_document_create_empty_title():
    """2. Empty title fails validation."""
    with pytest.raises(ValidationError):
        SourceDocumentCreate(
            title="  ",  # stripped to empty
            source_type="web"
        )


def test_source_document_create_too_short_source_type():
    """3. Too-short source_type fails validation."""
    with pytest.raises(ValidationError):
        SourceDocumentCreate(
            title="Valid Title",
            source_type="a"  # min_length is 2
        )


# ── DocumentChunkCreate Tests ────────────────────────────────────────────────

def test_document_chunk_create_valid():
    """4. Valid chunk data passes validation."""
    doc_id = uuid4()
    schema = DocumentChunkCreate(
        document_id=doc_id,
        chunk_index=0,
        chunk_text="This is chunk 1 content.",
        token_count=120,
        embedding_model="text-embedding-3-small",
        embedding_status="pending"
    )
    assert schema.document_id == doc_id
    assert schema.chunk_index == 0
    assert schema.token_count == 120


def test_document_chunk_create_chunk_index_below_0():
    """5. chunk_index below 0 fails validation."""
    with pytest.raises(ValidationError):
        DocumentChunkCreate(
            document_id=uuid4(),
            chunk_index=-1,
            chunk_text="Some text"
        )


def test_document_chunk_create_empty_chunk_text():
    """6. Empty chunk_text fails validation."""
    with pytest.raises(ValidationError):
        DocumentChunkCreate(
            document_id=uuid4(),
            chunk_index=0,
            chunk_text="   "  # stripped to empty
        )


def test_document_chunk_create_token_count_below_0():
    """7. token_count below 0 fails validation."""
    with pytest.raises(ValidationError):
        DocumentChunkCreate(
            document_id=uuid4(),
            chunk_index=0,
            chunk_text="Some text",
            token_count=-5
        )


# ── ChunkingRequest Tests ────────────────────────────────────────────────────

def test_chunking_request_valid():
    """8. Valid chunking parameters pass validation."""
    schema = ChunkingRequest(
        document_id=uuid4(),
        chunk_size=1000,
        chunk_overlap=150,
        strategy="recursive"
    )
    assert schema.chunk_size == 1000
    assert schema.chunk_overlap == 150
    assert schema.strategy == "recursive"


def test_chunking_request_size_below_200():
    """9. chunk_size below 200 fails validation."""
    with pytest.raises(ValidationError):
        ChunkingRequest(
            document_id=uuid4(),
            chunk_size=199,
            chunk_overlap=50
        )


def test_chunking_request_overlap_greater_than_size():
    """10. chunk_overlap greater than or equal to chunk_size fails validation."""
    with pytest.raises(ValidationError):
        ChunkingRequest(
            document_id=uuid4(),
            chunk_size=500,
            chunk_overlap=500  # overlap equal to size is forbidden
        )

    with pytest.raises(ValidationError):
        ChunkingRequest(
            document_id=uuid4(),
            chunk_size=500,
            chunk_overlap=600  # overlap greater than size is forbidden
        )


def test_chunking_request_invalid_strategy():
    """11. Invalid chunking strategy fails validation."""
    with pytest.raises(ValidationError):
        ChunkingRequest(
            document_id=uuid4(),
            chunk_size=1000,
            chunk_overlap=100,
            strategy="invalid_strat"
        )


# ── RetrievalRequest Tests ───────────────────────────────────────────────────

def test_retrieval_request_valid():
    """12. Valid retrieval parameters pass validation."""
    schema = RetrievalRequest(
        query="what is gross income?",
        top_k=5
    )
    assert schema.query == "what is gross income?"
    assert schema.top_k == 5


def test_retrieval_request_query_too_short():
    """13. Query too short (< 2 chars after stripping) fails validation."""
    with pytest.raises(ValidationError):
        RetrievalRequest(
            query=" q "  # stripped to "q" (length 1)
        )


def test_retrieval_request_top_k_below_1():
    """14. top_k below 1 fails validation."""
    with pytest.raises(ValidationError):
        RetrievalRequest(
            query="valid query",
            top_k=0
        )


def test_retrieval_request_top_k_above_20():
    """15. top_k above 20 fails validation."""
    with pytest.raises(ValidationError):
        RetrievalRequest(
            query="valid query",
            top_k=21
        )


# ── RetrievalResponse Tests ──────────────────────────────────────────────────

def test_retrieval_response_valid():
    """16. Valid retrieval response passes validation."""
    chunk_id = uuid4()
    doc_id = uuid4()
    item = RetrievalResultItem(
        chunk_id=chunk_id,
        document_id=doc_id,
        book_id=None,
        chunk_text="Take-home pay details.",
        score=0.89,
        source_title="Guide"
    )
    
    schema = RetrievalResponse(
        query="what is net income?",
        top_k=1,
        results=[item],
        total_results=1,
        status="success"
    )
    assert schema.query == "what is net income?"
    assert schema.results[0].chunk_id == chunk_id
    assert schema.results[0].score == 0.89


# ── ORM Responses Tests ──────────────────────────────────────────────────────

def test_source_document_response_orm():
    """17. SourceDocumentResponse can validate from ORM-like object (from_attributes)."""
    class MockDocModel:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.title = "Core Budgeting Guide"
            self.source_type = "manual"
            self.source_url = None
            self.raw_text = "Manual text here..."
            self.document_metadata = {"created_by": "user"}
            self.status = "processed"
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockDocModel()
    schema = SourceDocumentResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.title == "Core Budgeting Guide"
    assert schema.status == "processed"


def test_document_chunk_response_orm():
    """18. DocumentChunkResponse can validate from ORM-like object (from_attributes)."""
    class MockChunkModel:
        def __init__(self):
            self.id = uuid4()
            self.document_id = uuid4()
            self.book_id = uuid4()
            self.chunk_index = 4
            self.chunk_text = "Detailed budgeting steps"
            self.token_count = 50
            self.chunk_metadata = {"step": 2}
            self.embedding_model = "text-embedding-3-small"
            self.embedding_status = "completed"
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockChunkModel()
    schema = DocumentChunkResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.chunk_text == "Detailed budgeting steps"
    assert schema.embedding_status == "completed"
