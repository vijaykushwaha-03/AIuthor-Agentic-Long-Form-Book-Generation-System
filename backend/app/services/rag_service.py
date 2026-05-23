"""
AIuthor Backend — RAG Services.

Provides SourceDocumentService and DocumentChunkService for managing
source documents and their text chunks.

Neither service performs real embeddings, vector search, or external calls.
Embedding status is tracked as metadata only.  Real vector operations will
be implemented in Module 6 (pgvector).
"""
from __future__ import annotations

import logging
import math
from uuid import UUID

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models import BookProject, SourceDocument, DocumentChunk
from app.schemas.rag import (
    SourceDocumentCreate,
    SourceDocumentUpdate,
    DocumentChunkCreate,
    DocumentChunkUpdate,
    ChunkingRequest,
    ChunkingResponse,
)
from app.services.exceptions import (
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# SourceDocumentService
# ══════════════════════════════════════════════════════════════════════════════

class SourceDocumentService:
    """
    Service layer for SourceDocument CRUD and status tracking.

    All write operations commit + refresh within _commit(); any DB error
    causes a rollback before re-raising.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _get_book_or_404(self, book_id: UUID) -> BookProject:
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _get_document_or_404(
        self,
        document_id: UUID,
        book_id: UUID | None = None,
    ) -> SourceDocument:
        query = self.db.query(SourceDocument).filter(SourceDocument.id == document_id)
        if book_id is not None:
            query = query.filter(SourceDocument.book_id == book_id)
        doc = query.first()
        if doc is None:
            raise NotFoundError(
                message="Source document not found",
                code="document_not_found",
                details={"document_id": str(document_id)},
            )
        return doc

    # ── Public methods ────────────────────────────────────────────────────────

    def create_source_document(
        self,
        payload: SourceDocumentCreate,
        book_id: UUID | None = None,
    ) -> SourceDocument:
        """
        Create and persist a new SourceDocument.

        Args:
            payload:  Validated SourceDocumentCreate schema.
            book_id:  When provided from a route path, used as the source of
                      truth — overrides any book_id in the payload body.

        Raises:
            NotFoundError: If the resolved book_id does not correspond to a
                           known BookProject.
        """
        effective_book_id = book_id if book_id is not None else payload.book_id
        if effective_book_id != (book_id if book_id is not None else payload.book_id):
            logger.warning(
                "payload.book_id=%s overridden by path book_id=%s",
                payload.book_id,
                book_id,
            )

        if effective_book_id is not None:
            self._get_book_or_404(effective_book_id)

        doc = SourceDocument(
            book_id=effective_book_id,
            title=payload.title,
            source_type=payload.source_type,
            source_url=payload.source_url,
            raw_text=payload.raw_text,
            document_metadata=payload.document_metadata,
            status=payload.status or "created",
        )
        self.db.add(doc)
        self._commit()
        self.db.refresh(doc)
        logger.info("Created SourceDocument id=%s book_id=%s", doc.id, effective_book_id)
        return doc

    def get_source_document(self, document_id: UUID) -> SourceDocument:
        """
        Fetch a SourceDocument by id.

        Raises:
            NotFoundError: If the document does not exist.
        """
        return self._get_document_or_404(document_id)

    def get_source_document_for_book(
        self,
        book_id: UUID,
        document_id: UUID,
    ) -> SourceDocument:
        """
        Fetch a SourceDocument scoped to a specific book.

        Raises:
            NotFoundError: If the book or document does not exist.
        """
        self._get_book_or_404(book_id)
        return self._get_document_or_404(document_id, book_id=book_id)

    def list_source_documents(
        self,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        source_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[SourceDocument], int]:
        """
        Return a paginated, filtered list of SourceDocuments.

        Raises:
            NotFoundError: If book_id is provided but not found.

        Returns:
            Tuple of (items sorted newest-first, total_count).
        """
        if book_id is not None:
            self._get_book_or_404(book_id)

        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = self.db.query(SourceDocument).order_by(desc(SourceDocument.created_at))

        if book_id is not None:
            query = query.filter(SourceDocument.book_id == book_id)
        if status is not None:
            query = query.filter(SourceDocument.status == status)
        if source_type is not None:
            query = query.filter(SourceDocument.source_type == source_type)
        if search is not None:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    SourceDocument.title.ilike(pattern),
                    SourceDocument.source_url.ilike(pattern),
                    SourceDocument.raw_text.ilike(pattern),
                )
            )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total

    def update_source_document(
        self,
        document_id: UUID,
        payload: SourceDocumentUpdate,
        book_id: UUID | None = None,
    ) -> SourceDocument:
        """
        Apply a partial update to a SourceDocument.

        Raises:
            NotFoundError: If the document does not exist.
        """
        doc = self._get_document_or_404(document_id, book_id=book_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)
        self._commit()
        self.db.refresh(doc)
        logger.info("Updated SourceDocument id=%s fields=%s", document_id, list(update_data))
        return doc

    def delete_source_document(
        self,
        document_id: UUID,
        book_id: UUID | None = None,
    ) -> bool:
        """
        Permanently delete a SourceDocument (cascades to DocumentChunks).

        Raises:
            NotFoundError: If the document does not exist.
        """
        doc = self._get_document_or_404(document_id, book_id=book_id)
        self.db.delete(doc)
        self._commit()
        logger.info("Deleted SourceDocument id=%s", document_id)
        return True

    def mark_document_status(
        self,
        document_id: UUID,
        status: str,
    ) -> SourceDocument:
        """
        Update the status of a SourceDocument.

        Raises:
            NotFoundError: If the document does not exist.
        """
        doc = self._get_document_or_404(document_id)
        doc.status = status
        self._commit()
        self.db.refresh(doc)
        logger.info("SourceDocument id=%s status→%s", document_id, status)
        return doc


# ══════════════════════════════════════════════════════════════════════════════
# DocumentChunkService
# ══════════════════════════════════════════════════════════════════════════════

class DocumentChunkService:
    """
    Service layer for DocumentChunk CRUD, status tracking, and simple
    deterministic text chunking.

    Does NOT create embeddings or perform vector search.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _get_document_or_404(self, document_id: UUID) -> SourceDocument:
        doc = self.db.get(SourceDocument, document_id)
        if doc is None:
            raise NotFoundError(
                message="Source document not found",
                code="document_not_found",
                details={"document_id": str(document_id)},
            )
        return doc

    def _get_chunk_or_404(
        self,
        chunk_id: UUID,
        document_id: UUID | None = None,
    ) -> DocumentChunk:
        query = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id)
        if document_id is not None:
            query = query.filter(DocumentChunk.document_id == document_id)
        chunk = query.first()
        if chunk is None:
            raise NotFoundError(
                message="Document chunk not found",
                code="chunk_not_found",
                details={"chunk_id": str(chunk_id)},
            )
        return chunk

    def _chunk_index_exists(self, document_id: UUID, chunk_index: int) -> bool:
        return (
            self.db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_index == chunk_index,
            )
            .count()
            > 0
        )

    def _max_chunk_index(self, document_id: UUID) -> int:
        """Return current max chunk_index for a document, or -1 if none."""
        from sqlalchemy import func
        result = (
            self.db.query(func.max(DocumentChunk.chunk_index))
            .filter(DocumentChunk.document_id == document_id)
            .scalar()
        )
        return result if result is not None else -1

    @staticmethod
    def _simple_split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        """
        Deterministic character-window text splitter.

        Slides a window of ``chunk_size`` characters across ``text`` with a
        step of ``chunk_size - chunk_overlap``.  Always produces at least one
        chunk even when text is shorter than chunk_size.
        """
        chunks: list[str] = []
        step = max(1, chunk_size - chunk_overlap)
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += step
        return chunks if chunks else [text.strip()]

    @staticmethod
    def _approx_token_count(text: str) -> int:
        """Approximate token count using whitespace word count."""
        return len(text.split())

    # ── Public methods ────────────────────────────────────────────────────────

    def create_chunk(
        self,
        payload: DocumentChunkCreate,
        document_id: UUID | None = None,
    ) -> DocumentChunk:
        """
        Create and persist a new DocumentChunk.

        Args:
            payload:     Validated DocumentChunkCreate schema.
            document_id: When provided from a route path, used as source of truth.

        Raises:
            NotFoundError: If the SourceDocument does not exist.
            ConflictError: If chunk_index already exists for this document.
        """
        effective_doc_id = document_id if document_id is not None else payload.document_id
        doc = self._get_document_or_404(effective_doc_id)

        # Inherit book_id from parent document when not specified
        book_id = payload.book_id if payload.book_id is not None else doc.book_id

        if self._chunk_index_exists(effective_doc_id, payload.chunk_index):
            raise ConflictError(
                message=f"Chunk index {payload.chunk_index} already exists for this document",
                code="duplicate_chunk_index",
                details={
                    "document_id": str(effective_doc_id),
                    "chunk_index": payload.chunk_index,
                },
            )

        chunk = DocumentChunk(
            document_id=effective_doc_id,
            book_id=book_id,
            chunk_index=payload.chunk_index,
            chunk_text=payload.chunk_text,
            token_count=payload.token_count,
            chunk_metadata=payload.chunk_metadata,
            embedding_model=payload.embedding_model,
            embedding_status=payload.embedding_status or "pending",
        )
        self.db.add(chunk)
        self._commit()
        self.db.refresh(chunk)
        logger.info(
            "Created DocumentChunk id=%s chunk_index=%s for document_id=%s",
            chunk.id,
            chunk.chunk_index,
            effective_doc_id,
        )
        return chunk

    def get_chunk(self, chunk_id: UUID) -> DocumentChunk:
        """Fetch a DocumentChunk by id. Raises NotFoundError if missing."""
        return self._get_chunk_or_404(chunk_id)

    def get_chunk_for_document(
        self,
        document_id: UUID,
        chunk_id: UUID,
    ) -> DocumentChunk:
        """Fetch a DocumentChunk scoped to a document. Raises NotFoundError if missing."""
        return self._get_chunk_or_404(chunk_id, document_id=document_id)

    def list_chunks(
        self,
        document_id: UUID | None = None,
        book_id: UUID | None = None,
        page: int = 1,
        page_size: int = 50,
        embedding_status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[DocumentChunk], int]:
        """
        Return a paginated, filtered list of DocumentChunks.

        Returns:
            Tuple of (items sorted by chunk_index asc, total_count).
        """
        page = max(1, page)
        page_size = max(1, min(100, page_size))

        query = (
            self.db.query(DocumentChunk)
            .order_by(asc(DocumentChunk.chunk_index))
        )

        if document_id is not None:
            query = query.filter(DocumentChunk.document_id == document_id)
        if book_id is not None:
            query = query.filter(DocumentChunk.book_id == book_id)
        if embedding_status is not None:
            query = query.filter(DocumentChunk.embedding_status == embedding_status)
        if search is not None:
            query = query.filter(DocumentChunk.chunk_text.ilike(f"%{search}%"))

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update_chunk(
        self,
        chunk_id: UUID,
        payload: DocumentChunkUpdate,
        document_id: UUID | None = None,
    ) -> DocumentChunk:
        """
        Apply a partial update to a DocumentChunk.

        Does NOT update vector fields.

        Raises:
            NotFoundError: If the chunk does not exist.
        """
        chunk = self._get_chunk_or_404(chunk_id, document_id=document_id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(chunk, field, value)
        self._commit()
        self.db.refresh(chunk)
        logger.info("Updated DocumentChunk id=%s fields=%s", chunk_id, list(update_data))
        return chunk

    def delete_chunk(
        self,
        chunk_id: UUID,
        document_id: UUID | None = None,
    ) -> bool:
        """
        Permanently delete a DocumentChunk.

        Raises:
            NotFoundError: If the chunk does not exist.
        """
        chunk = self._get_chunk_or_404(chunk_id, document_id=document_id)
        self.db.delete(chunk)
        self._commit()
        logger.info("Deleted DocumentChunk id=%s", chunk_id)
        return True

    def mark_embedding_status(
        self,
        chunk_id: UUID,
        embedding_status: str,
        embedding_model: str | None = None,
    ) -> DocumentChunk:
        """
        Update embedding_status (and optionally embedding_model) for a chunk.

        Does NOT store any vector.

        Raises:
            NotFoundError: If the chunk does not exist.
        """
        chunk = self._get_chunk_or_404(chunk_id)
        chunk.embedding_status = embedding_status
        if embedding_model is not None:
            chunk.embedding_model = embedding_model
        self._commit()
        self.db.refresh(chunk)
        logger.info(
            "DocumentChunk id=%s embedding_status→%s model=%s",
            chunk_id,
            embedding_status,
            embedding_model,
        )
        return chunk

    def simple_chunk_document_text(
        self,
        document_id: UUID,
        request: ChunkingRequest,
    ) -> ChunkingResponse:
        """
        Split a SourceDocument's raw_text into DocumentChunk records using a
        simple deterministic character-window splitter.

        This is a **local-only** operation — no LLM, no embeddings, no
        external services are called.  Chunks are appended after the current
        maximum chunk_index to allow incremental chunking.

        Args:
            document_id: The SourceDocument whose raw_text will be split.
            request:     ChunkingRequest with chunk_size, chunk_overlap, strategy.

        Raises:
            NotFoundError:          If the document does not exist.
            ValidationServiceError: If raw_text is empty or missing.

        Returns:
            ChunkingResponse with counts and config echo.
        """
        doc = self._get_document_or_404(document_id)

        if not doc.raw_text or not doc.raw_text.strip():
            raise ValidationServiceError(
                message="Document has no raw_text to chunk",
                code="empty_raw_text",
                details={"document_id": str(document_id)},
            )

        text_segments = self._simple_split(
            doc.raw_text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        # Append after existing max chunk_index to support incremental chunking
        base_index = self._max_chunk_index(document_id) + 1

        new_chunks: list[DocumentChunk] = []
        for offset, segment in enumerate(text_segments):
            chunk = DocumentChunk(
                document_id=document_id,
                book_id=doc.book_id,
                chunk_index=base_index + offset,
                chunk_text=segment,
                token_count=self._approx_token_count(segment),
                embedding_status="pending",
            )
            self.db.add(chunk)
            new_chunks.append(chunk)

        self._commit()
        for c in new_chunks:
            self.db.refresh(c)

        logger.info(
            "Chunked document_id=%s into %d chunks (chunk_size=%d, overlap=%d)",
            document_id,
            len(new_chunks),
            request.chunk_size,
            request.chunk_overlap,
        )

        return ChunkingResponse(
            document_id=document_id,
            chunks_created=len(new_chunks),
            strategy=request.strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            status="completed",
            message=(
                f"Created {len(new_chunks)} chunks using simple character-window splitter. "
                "No embeddings generated — set embedding_status='pending' for all chunks."
            ),
        )
