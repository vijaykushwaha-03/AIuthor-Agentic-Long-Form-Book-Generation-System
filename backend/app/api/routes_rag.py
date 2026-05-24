"""
AIuthor Backend — RAG API Routes.

Tags: rag

Endpoint groups:

  Source Documents (book-scoped):
    POST   /api/books/{book_id}/sources
    GET    /api/books/{book_id}/sources
    GET    /api/books/{book_id}/sources/{document_id}
    PATCH  /api/books/{book_id}/sources/{document_id}
    DELETE /api/books/{book_id}/sources/{document_id}

  Source Document cross-book status:
    PATCH  /api/sources/{document_id}/status

  Document Chunks (document-scoped):
    POST   /api/sources/{document_id}/chunks
    GET    /api/sources/{document_id}/chunks
    GET    /api/sources/{document_id}/chunks/{chunk_id}
    PATCH  /api/sources/{document_id}/chunks/{chunk_id}
    DELETE /api/sources/{document_id}/chunks/{chunk_id}

  Chunk cross-document status:
    PATCH  /api/chunks/{chunk_id}/embedding-status

  Utility:
    POST   /api/sources/{document_id}/chunk   — simple local chunker (no LLM/embeddings)
    POST   /api/rag/retrieve                  — lexical ILIKE retrieval (no vectors)

  Module 6.0B — Embedding & Semantic Retrieval:
    GET    /api/rag/pgvector-status           — check pgvector extension availability
    POST   /api/chunks/{chunk_id}/embed       — embed a single chunk
    POST   /api/sources/{document_id}/embed-chunks — bulk-embed source document chunks
    POST   /api/books/{book_id}/embed-chunks  — bulk-embed all book chunks
    POST   /api/rag/semantic-retrieve         — semantic vector retrieval

NOTE: /chunk and /chunks for a document are declared before /{chunk_id} to
prevent FastAPI from treating literal strings as UUIDs.
"""
from __future__ import annotations

import math
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.error_handlers import handle_service_error
from app.db.pgvector_check import get_pgvector_status
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
    # Module 6.0B
    ChunkEmbeddingRequest,
    ChunkEmbeddingResponse,
    BulkChunkEmbeddingRequest,
    BulkChunkEmbeddingResponse,
    SemanticRetrievalRequest,
    SemanticRetrievalResponse,
    PaginatedResponse,
    MessageResponse,
    # Module 6.1
    HybridRetrievalRequest,
    HybridRetrievalResponse,
    ContextPackRequest,
    ContextPackResponse,
)
from app.services import (
    SourceDocumentService,
    DocumentChunkService,
    ChunkEmbeddingService,
    SemanticRetrievalService,
    HybridRetrievalService,
    ContextPackService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)
from app.services.embedding_service import EmbeddingService
from app.models import DocumentChunk, SourceDocument

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag"])

# ── Dependency ────────────────────────────────────────────────────────────────

DbDep = Annotated[Session, Depends(get_db)]


def _doc_service(db: DbDep) -> SourceDocumentService:
    return SourceDocumentService(db)


def _chunk_service(db: DbDep) -> DocumentChunkService:
    return DocumentChunkService(db)


DocServiceDep = Annotated[SourceDocumentService, Depends(_doc_service)]
ChunkServiceDep = Annotated[DocumentChunkService, Depends(_chunk_service)]


# ══════════════════════════════════════════════════════════════════════════════
# Source Document Endpoints — book-scoped
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/books/{book_id}/sources",
    response_model=SourceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a source document",
    description=(
        "Create a new source document linked to a book project. "
        "Path book_id is used as the source of truth."
    ),
)
def create_source_document(
    book_id: UUID,
    payload: SourceDocumentCreate,
    svc: DocServiceDep,
) -> SourceDocumentResponse:
    try:
        doc = svc.create_source_document(payload, book_id=book_id)
        return SourceDocumentResponse.model_validate(doc)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/sources",
    response_model=PaginatedResponse[SourceDocumentListItem],
    summary="List source documents for a book",
)
def list_source_documents_for_book(
    book_id: UUID,
    svc: DocServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    source_type: str | None = Query(None),
    search: str | None = Query(None),
) -> PaginatedResponse[SourceDocumentListItem]:
    try:
        items, total = svc.list_source_documents(
            book_id=book_id,
            page=page,
            page_size=page_size,
            status=status_filter,
            source_type=source_type,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[SourceDocumentListItem.model_validate(d) for d in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/books/{book_id}/sources/{document_id}",
    response_model=SourceDocumentResponse,
    summary="Get a source document",
)
def get_source_document_for_book(
    book_id: UUID,
    document_id: UUID,
    svc: DocServiceDep,
) -> SourceDocumentResponse:
    try:
        doc = svc.get_source_document_for_book(book_id, document_id)
        return SourceDocumentResponse.model_validate(doc)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/books/{book_id}/sources/{document_id}",
    response_model=SourceDocumentResponse,
    summary="Update a source document",
)
def update_source_document_for_book(
    book_id: UUID,
    document_id: UUID,
    payload: SourceDocumentUpdate,
    svc: DocServiceDep,
) -> SourceDocumentResponse:
    try:
        doc = svc.update_source_document(document_id, payload, book_id=book_id)
        return SourceDocumentResponse.model_validate(doc)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/books/{book_id}/sources/{document_id}",
    response_model=MessageResponse,
    summary="Delete a source document",
)
def delete_source_document_for_book(
    book_id: UUID,
    document_id: UUID,
    svc: DocServiceDep,
) -> MessageResponse:
    try:
        svc.delete_source_document(document_id, book_id=book_id)
        return MessageResponse(message=f"Source document {document_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ── Cross-book status update ──────────────────────────────────────────────────

@router.patch(
    "/api/sources/{document_id}/status",
    response_model=SourceDocumentResponse,
    summary="Update source document status",
    description="Set a source document's status (e.g. created → parsed → indexed).",
)
def mark_source_document_status(
    document_id: UUID,
    svc: DocServiceDep,
    status_value: str = Body(..., embed=True, alias="status"),
) -> SourceDocumentResponse:
    try:
        doc = svc.mark_document_status(document_id, status_value)
        return SourceDocumentResponse.model_validate(doc)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Document Chunk Endpoints — document-scoped
# NOTE: /chunk (chunker) and /chunks (list/create) are declared BEFORE
#       /{chunk_id} so FastAPI does not try to parse literals as UUIDs.
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/sources/{document_id}/chunk",
    response_model=ChunkingResponse,
    status_code=status.HTTP_200_OK,
    summary="Chunk a source document's raw text",
    description=(
        "Split the document's raw_text into DocumentChunk records using a simple "
        "deterministic character-window splitter. "
        "No LLM, no embeddings, no external services are used. "
        "All created chunks have embedding_status='pending'."
    ),
)
def chunk_document(
    document_id: UUID,
    payload: ChunkingRequest,
    svc: ChunkServiceDep,
) -> ChunkingResponse:
    try:
        return svc.simple_chunk_document_text(document_id, payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/sources/{document_id}/chunks",
    response_model=DocumentChunkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document chunk",
    description="Manually create a single chunk record. Path document_id is the source of truth.",
)
def create_chunk(
    document_id: UUID,
    payload: DocumentChunkCreate,
    svc: ChunkServiceDep,
) -> DocumentChunkResponse:
    try:
        chunk = svc.create_chunk(payload, document_id=document_id)
        return DocumentChunkResponse.model_validate(chunk)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/sources/{document_id}/chunks",
    response_model=PaginatedResponse[DocumentChunkListItem],
    summary="List chunks for a document",
)
def list_chunks_for_document(
    document_id: UUID,
    svc: ChunkServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    embedding_status_filter: str | None = Query(None, alias="embedding_status"),
    search: str | None = Query(None),
) -> PaginatedResponse[DocumentChunkListItem]:
    try:
        items, total = svc.list_chunks(
            document_id=document_id,
            page=page,
            page_size=page_size,
            embedding_status=embedding_status_filter,
            search=search,
        )
        pages = math.ceil(total / page_size) if page_size else 0
        return PaginatedResponse(
            items=[DocumentChunkListItem.model_validate(c) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.get(
    "/api/sources/{document_id}/chunks/{chunk_id}",
    response_model=DocumentChunkResponse,
    summary="Get a document chunk",
)
def get_chunk_for_document(
    document_id: UUID,
    chunk_id: UUID,
    svc: ChunkServiceDep,
) -> DocumentChunkResponse:
    try:
        chunk = svc.get_chunk_for_document(document_id, chunk_id)
        return DocumentChunkResponse.model_validate(chunk)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.patch(
    "/api/sources/{document_id}/chunks/{chunk_id}",
    response_model=DocumentChunkResponse,
    summary="Update a document chunk",
)
def update_chunk(
    document_id: UUID,
    chunk_id: UUID,
    payload: DocumentChunkUpdate,
    svc: ChunkServiceDep,
) -> DocumentChunkResponse:
    try:
        chunk = svc.update_chunk(chunk_id, payload, document_id=document_id)
        return DocumentChunkResponse.model_validate(chunk)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.delete(
    "/api/sources/{document_id}/chunks/{chunk_id}",
    response_model=MessageResponse,
    summary="Delete a document chunk",
)
def delete_chunk(
    document_id: UUID,
    chunk_id: UUID,
    svc: ChunkServiceDep,
) -> MessageResponse:
    try:
        svc.delete_chunk(chunk_id, document_id=document_id)
        return MessageResponse(message=f"Chunk {chunk_id} deleted successfully.")
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ── Cross-document embedding status ───────────────────────────────────────────

@router.patch(
    "/api/chunks/{chunk_id}/embedding-status",
    response_model=DocumentChunkResponse,
    summary="Update chunk embedding status",
    description=(
        "Update a chunk's embedding_status and optionally embedding_model. "
        "Does NOT store any vector data. "
        "Real embeddings will be added in Module 6 (pgvector)."
    ),
)
def mark_chunk_embedding_status(
    chunk_id: UUID,
    svc: ChunkServiceDep,
    embedding_status: str = Body(..., embed=True),
    embedding_model: str | None = Body(None, embed=True),
) -> DocumentChunkResponse:
    try:
        chunk = svc.mark_embedding_status(chunk_id, embedding_status, embedding_model)
        return DocumentChunkResponse.model_validate(chunk)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Placeholder Lexical Retrieval
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/rag/retrieve",
    response_model=RetrievalResponse,
    summary="Lexical keyword retrieval (placeholder)",
    description=(
        "Performs simple ILIKE SQL keyword search over chunk_text. "
        "This is a placeholder endpoint to validate the API contract. "
        "**No vector search, no embeddings, no pgvector** are used. "
        "Real semantic retrieval will be implemented in Module 6."
    ),
)
def retrieve(
    payload: RetrievalRequest,
    db: DbDep,
) -> RetrievalResponse:
    try:
        query = (
            db.query(DocumentChunk, SourceDocument)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .filter(DocumentChunk.chunk_text.ilike(f"%{payload.query}%"))
        )
        if payload.book_id is not None:
            query = query.filter(DocumentChunk.book_id == payload.book_id)

        rows = query.limit(payload.top_k).all()

        results: list[RetrievalResultItem] = []
        for chunk, doc in rows:
            chunk_text = chunk.chunk_text if payload.include_raw_text else None
            results.append(
                RetrievalResultItem(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    book_id=chunk.book_id,
                    chunk_text=chunk_text,
                    score=1.0,            # flat score for lexical matches
                    source_title=doc.title,
                    source_url=doc.source_url,
                    metadata=chunk.chunk_metadata,
                )
            )

        return RetrievalResponse(
            query=payload.query,
            top_k=payload.top_k,
            results=results,
            total_results=len(results),
            status="ok",
            message=(
                "Lexical ILIKE retrieval. "
                "For semantic vector search use POST /api/rag/semantic-retrieve."
            ),
        )
    except Exception as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Module 6.0B: pgvector Status, Embedding, and Semantic Retrieval Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/api/rag/pgvector-status",
    summary="pgvector extension availability",
    description=(
        "Check whether the pgvector extension is installed on the connected database. "
        "Returns False on SQLite (test) databases without raising errors."
    ),
)
def pgvector_status(db: DbDep) -> dict:
    try:
        return get_pgvector_status(db)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/api/chunks/{chunk_id}/embed",
    response_model=ChunkEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Embed a single document chunk",
    description=(
        "Generate an embedding vector for the specified DocumentChunk and persist it. "
        "Uses the configured EMBEDDING_PROVIDER (default: gemini). "
        "In tests, always use a mock provider via the force/provider fields."
    ),
)
def embed_chunk(
    chunk_id: UUID,
    payload: ChunkEmbeddingRequest,
    db: DbDep,
) -> ChunkEmbeddingResponse:
    try:
        from app.config import get_settings
        settings = get_settings()
        # In test environments EMBEDDING_PROVIDER=mock is set in conftest.
        # For production, the factory resolves the real provider.
        from app.embeddings.factory import get_embedding_provider
        if payload.provider:
            provider = get_embedding_provider(payload.provider)
        else:
            provider = get_embedding_provider()
        svc = ChunkEmbeddingService(
            db=db,
            embedding_service=EmbeddingService(provider=provider),
        )
        chunk = svc.embed_chunk(chunk_id, provider=None, force=payload.force)
        return ChunkEmbeddingResponse(
            chunk_id=chunk.id,
            embedding_status=chunk.embedding_status,
            embedding_provider=chunk.embedding_provider,
            embedding_model=chunk.embedding_model,
            embedding_dimensions=chunk.embedding_dimensions,
            message=(
                f"Chunk {chunk_id} embedded successfully."
                if chunk.embedding_status == "completed"
                else f"Chunk {chunk_id} status: {chunk.embedding_status}."
            ),
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/sources/{document_id}/embed-chunks",
    response_model=BulkChunkEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk-embed all chunks for a source document",
    description=(
        "Generate and persist embedding vectors for all pending chunks of a SourceDocument. "
        "Skips already-completed chunks unless force=True."
    ),
)
def embed_source_chunks(
    document_id: UUID,
    payload: BulkChunkEmbeddingRequest,
    db: DbDep,
) -> BulkChunkEmbeddingResponse:
    try:
        from app.embeddings.factory import get_embedding_provider
        if payload.provider:
            provider = get_embedding_provider(payload.provider)
        else:
            provider = get_embedding_provider()
        svc = ChunkEmbeddingService(
            db=db,
            embedding_service=EmbeddingService(provider=provider),
        )
        return svc.embed_document_chunks(
            document_id=document_id,
            force=payload.force,
            batch_size=payload.batch_size,
            limit=payload.limit,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/books/{book_id}/embed-chunks",
    response_model=BulkChunkEmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk-embed all chunks for a book",
    description=(
        "Generate and persist embedding vectors for all pending chunks belonging to a BookProject. "
        "Skips already-completed chunks unless force=True."
    ),
)
def embed_book_chunks(
    book_id: UUID,
    payload: BulkChunkEmbeddingRequest,
    db: DbDep,
) -> BulkChunkEmbeddingResponse:
    try:
        from app.embeddings.factory import get_embedding_provider
        if payload.provider:
            provider = get_embedding_provider(payload.provider)
        else:
            provider = get_embedding_provider()
        svc = ChunkEmbeddingService(
            db=db,
            embedding_service=EmbeddingService(provider=provider),
        )
        return svc.embed_book_chunks(
            book_id=book_id,
            force=payload.force,
            batch_size=payload.batch_size,
            limit=payload.limit,
        )
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/rag/semantic-retrieve",
    response_model=SemanticRetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic vector retrieval",
    description=(
        "Embed the query text and return the top-K most semantically similar chunks. "
        "Uses pgvector cosine distance on PostgreSQL; "
        "falls back to Python cosine similarity on SQLite/test databases. "
        "Does NOT affect the existing lexical POST /api/rag/retrieve endpoint."
    ),
)
def semantic_retrieve(
    payload: SemanticRetrievalRequest,
    db: DbDep,
) -> SemanticRetrievalResponse:
    try:
        from app.embeddings.factory import get_embedding_provider
        if payload.provider:
            provider = get_embedding_provider(payload.provider)
        else:
            provider = get_embedding_provider()
        svc = SemanticRetrievalService(
            db=db,
            embedding_service=EmbeddingService(provider=provider),
        )
        return svc.semantic_retrieve(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
# Module 6.1: Hybrid Retrieval & Context Pack Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/api/rag/hybrid-retrieve",
    response_model=HybridRetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid lexical + semantic retrieval",
    description=(
        "Combines semantic (vector) similarity and lexical matching to return "
        "relevance-ranked chunks with local citation tags (C1, C2...)."
    ),
)
def hybrid_retrieve(
    payload: HybridRetrievalRequest,
    db: DbDep,
) -> HybridRetrievalResponse:
    try:
        from app.embeddings.factory import get_embedding_provider
        if payload.provider:
            provider = get_embedding_provider(payload.provider)
        else:
            provider = get_embedding_provider()
        semantic_svc = SemanticRetrievalService(
            db=db,
            embedding_service=EmbeddingService(provider=provider),
        )
        svc = HybridRetrievalService(db=db, semantic_service=semantic_svc)
        return svc.hybrid_retrieve(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)


@router.post(
    "/api/rag/context-pack",
    response_model=ContextPackResponse,
    status_code=status.HTTP_200_OK,
    summary="Build agent-ready RAG context pack",
    description=(
        "Retrieves relevance-ranked chunks and packages them into a single stable "
        "structured text context, annotated with citation markers, respecting length boundaries."
    ),
)
def build_context_pack(
    payload: ContextPackRequest,
    db: DbDep,
) -> ContextPackResponse:
    try:
        from app.embeddings.factory import get_embedding_provider
        if payload.provider:
            provider = get_embedding_provider(payload.provider)
        else:
            provider = get_embedding_provider()
        semantic_svc = SemanticRetrievalService(
            db=db,
            embedding_service=EmbeddingService(provider=provider),
        )
        hybrid_svc = HybridRetrievalService(db=db, semantic_service=semantic_svc)
        svc = ContextPackService(db=db, hybrid_service=hybrid_svc)
        return svc.build_context_pack(payload)
    except (NotFoundError, ValidationServiceError, ConflictError, Exception) as exc:
        handle_service_error(exc)

