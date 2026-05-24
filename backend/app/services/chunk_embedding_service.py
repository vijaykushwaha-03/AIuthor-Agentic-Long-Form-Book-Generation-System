"""
AIuthor Backend — Chunk Embedding Service (Module 6.0B).

Responsible for embedding stored DocumentChunk records using the configured
embedding provider and persisting the resulting vectors to the database.

Design decisions:
  - Uses EmbeddingService (from Module 6.0A) as the embedding backend.
  - All stored vectors must have exactly settings.RAG_VECTOR_DIMENSIONS.
  - No external API calls are made unless a real provider is injected.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import get_settings
from app.embeddings.factory import get_embedding_provider
from app.embeddings.schemas import EmbeddingRequest
from app.models.document import DocumentChunk, SourceDocument
from app.models.book import BookProject
from app.schemas.rag import BulkChunkEmbeddingResponse
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import NotFoundError, ValidationServiceError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ChunkEmbeddingService:
    """
    Embeds DocumentChunk records and persists vectors to the database.

    Constructor:
        db:                Active SQLAlchemy Session.
        embedding_service: Optional injected EmbeddingService (for tests).
                           If None, the default provider from env is used.
    """

    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self._settings = get_settings()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit(self) -> None:
        """Commit the current transaction, rolling back on error."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _get_chunk(self, chunk_id: UUID) -> DocumentChunk:
        chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()
        if chunk is None:
            raise NotFoundError(f"DocumentChunk {chunk_id} not found.")
        return chunk

    def _get_document(self, document_id: UUID) -> SourceDocument:
        doc = self.db.query(SourceDocument).filter(SourceDocument.id == document_id).first()
        if doc is None:
            raise NotFoundError(f"SourceDocument {document_id} not found.")
        return doc

    def _get_book(self, book_id: UUID) -> BookProject:
        book = self.db.query(BookProject).filter(BookProject.id == book_id).first()
        if book is None:
            raise NotFoundError(f"BookProject {book_id} not found.")
        return book

    def _validate_vector_dimensions(self, vector: list[float], expected: int) -> None:
        if len(vector) != expected:
            raise ValidationServiceError(
                f"Vector dimension mismatch: expected {expected}, got {len(vector)}. "
                f"Ensure the embedding provider is configured to produce {expected}-dimensional vectors."
            )

    def _set_chunk_failed(self, chunk: DocumentChunk, message: str) -> None:
        """Mark a chunk as embedding-failed and flush without full commit."""
        try:
            chunk.embedding_status = "failed"
            chunk.embedding_error = message
            self.db.flush()
        except Exception:
            self.db.rollback()

    def _get_provider_for_request(self, provider_name: str | None) -> EmbeddingService:
        """
        Return the appropriate EmbeddingService.
        - If a provider name is given, build a new service with that provider.
        - Otherwise use the injected service (which may be mock in tests).
        """
        if provider_name:
            p = get_embedding_provider(provider_name)
            return EmbeddingService(provider=p)
        return self.embedding_service

    # ── Public methods ────────────────────────────────────────────────────────

    def embed_chunk(
        self,
        chunk_id: UUID,
        provider: str | None = None,
        force: bool = False,
    ) -> DocumentChunk:
        """
        Embed a single DocumentChunk and store the vector in the database.

        Args:
            chunk_id: UUID of the chunk to embed.
            provider: Optional provider override ('gemini', 'openai', 'mock').
            force:    If False, skip chunks already marked 'completed'.

        Returns:
            The updated DocumentChunk ORM object.

        Raises:
            NotFoundError:          Chunk does not exist.
            ValidationServiceError: Chunk text is empty, or dimension mismatch.
        """
        chunk = self._get_chunk(chunk_id)
        dims = self._settings.RAG_VECTOR_DIMENSIONS

        # Skip re-embedding unless forced
        if chunk.embedding_status == "completed" and not force:
            logger.debug("embed_chunk: chunk %s already completed, skipping.", chunk_id)
            return chunk

        # Validate text content
        if not chunk.chunk_text or not chunk.chunk_text.strip():
            self._set_chunk_failed(chunk, "chunk_text is empty — cannot embed.")
            self._commit()
            raise ValidationServiceError("Cannot embed a chunk with empty chunk_text.")

        svc = self._get_provider_for_request(provider)

        try:
            request = EmbeddingRequest(
                texts=[chunk.chunk_text],
                dimensions=dims,
                metadata={"chunk_id": str(chunk_id)},
            )
            response = svc.embed_texts(request)
        except Exception as exc:
            msg = f"Embedding provider failed: {exc}"
            self._set_chunk_failed(chunk, msg)
            self._commit()
            raise ValidationServiceError(msg) from exc

        if not response.items:
            msg = "Embedding provider returned no items."
            self._set_chunk_failed(chunk, msg)
            self._commit()
            raise ValidationServiceError(msg)

        vector = response.items[0].embedding

        # Dimension guard
        try:
            self._validate_vector_dimensions(vector, dims)
        except ValidationServiceError as exc:
            self._set_chunk_failed(chunk, str(exc))
            self._commit()
            raise

        # Persist
        chunk.embedding = vector
        chunk.embedding_status = "completed"
        chunk.embedding_provider = response.provider
        chunk.embedding_model = response.model
        chunk.embedding_dimensions = response.dimensions
        chunk.embedding_created_at = datetime.now(timezone.utc)
        chunk.embedding_error = None

        # Update token_count if not already set
        item = response.items[0]
        if item.token_count is not None and chunk.token_count is None:
            chunk.token_count = item.token_count

        self._commit()
        self.db.refresh(chunk)
        logger.debug("embed_chunk: chunk %s embedded, dims=%d.", chunk_id, dims)
        return chunk

    def embed_document_chunks(
        self,
        document_id: UUID,
        provider: str | None = None,
        force: bool = False,
        batch_size: int | None = None,
        limit: int | None = None,
    ) -> BulkChunkEmbeddingResponse:
        """
        Embed all pending chunks for a SourceDocument.

        Args:
            document_id: UUID of the source document.
            provider:    Optional provider override.
            force:       If True, re-embed already-completed chunks.
            batch_size:  Texts per embedding batch (default from settings).
            limit:       Max chunks to process in this run.

        Returns:
            BulkChunkEmbeddingResponse summarising the operation.
        """
        self._get_document(document_id)  # 404 guard
        dims = self._settings.RAG_VECTOR_DIMENSIONS
        effective_batch = batch_size or self._settings.EMBEDDING_BATCH_SIZE
        svc = self._get_provider_for_request(provider)

        # Determine candidates
        query = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        )
        if not force:
            query = query.filter(
                (DocumentChunk.embedding_status != "completed")
                | (DocumentChunk.embedding == None)  # noqa: E711
            )
        if limit:
            query = query.limit(limit)
        candidates = query.all()

        total = len(candidates)
        embedded = skipped = failed = 0
        errors: list[dict] = []
        last_provider = svc.provider.provider_name
        last_model = svc.provider.model_name

        for i in range(0, total, effective_batch):
            batch = candidates[i : i + effective_batch]
            texts = [c.chunk_text for c in batch]

            try:
                req = EmbeddingRequest(texts=texts, dimensions=dims)
                resp = svc.embed_texts(req)
                last_provider = resp.provider
                last_model = resp.model
            except Exception as exc:
                for c in batch:
                    self._set_chunk_failed(c, str(exc))
                    failed += 1
                    errors.append({"chunk_id": str(c.id), "error": str(exc)})
                self._commit()
                continue

            for j, chunk in enumerate(batch):
                if j >= len(resp.items):
                    failed += 1
                    continue
                item = resp.items[j]
                vec = item.embedding
                try:
                    self._validate_vector_dimensions(vec, dims)
                except ValidationServiceError as exc:
                    self._set_chunk_failed(chunk, str(exc))
                    failed += 1
                    errors.append({"chunk_id": str(chunk.id), "error": str(exc)})
                    continue

                chunk.embedding = vec
                chunk.embedding_status = "completed"
                chunk.embedding_provider = resp.provider
                chunk.embedding_model = resp.model
                chunk.embedding_dimensions = resp.dimensions
                chunk.embedding_created_at = datetime.now(timezone.utc)
                chunk.embedding_error = None
                if item.token_count is not None and chunk.token_count is None:
                    chunk.token_count = item.token_count
                embedded += 1

            self._commit()

        status_str = "completed" if failed == 0 else ("partial" if embedded > 0 else "failed")
        return BulkChunkEmbeddingResponse(
            target_type="document",
            target_id=document_id,
            total_candidates=total,
            embedded_count=embedded,
            skipped_count=skipped,
            failed_count=failed,
            provider=last_provider,
            model=last_model,
            dimensions=dims,
            status=status_str,
            errors=errors,
        )

    def embed_book_chunks(
        self,
        book_id: UUID,
        provider: str | None = None,
        force: bool = False,
        batch_size: int | None = None,
        limit: int | None = None,
    ) -> BulkChunkEmbeddingResponse:
        """
        Embed all pending chunks for a BookProject across all its source documents.

        Args:
            book_id:     UUID of the book project.
            provider:    Optional provider override.
            force:       If True, re-embed already-completed chunks.
            batch_size:  Texts per embedding batch.
            limit:       Max chunks to process.

        Returns:
            BulkChunkEmbeddingResponse summarising the operation.
        """
        self._get_book(book_id)  # 404 guard
        dims = self._settings.RAG_VECTOR_DIMENSIONS
        effective_batch = batch_size or self._settings.EMBEDDING_BATCH_SIZE
        svc = self._get_provider_for_request(provider)

        query = self.db.query(DocumentChunk).filter(
            DocumentChunk.book_id == book_id
        )
        if not force:
            query = query.filter(
                (DocumentChunk.embedding_status != "completed")
                | (DocumentChunk.embedding == None)  # noqa: E711
            )
        if limit:
            query = query.limit(limit)
        candidates = query.all()

        total = len(candidates)
        embedded = skipped = failed = 0
        errors: list[dict] = []
        last_provider = svc.provider.provider_name
        last_model = svc.provider.model_name

        for i in range(0, total, effective_batch):
            batch = candidates[i : i + effective_batch]
            texts = [c.chunk_text for c in batch]

            try:
                req = EmbeddingRequest(texts=texts, dimensions=dims)
                resp = svc.embed_texts(req)
                last_provider = resp.provider
                last_model = resp.model
            except Exception as exc:
                for c in batch:
                    self._set_chunk_failed(c, str(exc))
                    failed += 1
                    errors.append({"chunk_id": str(c.id), "error": str(exc)})
                self._commit()
                continue

            for j, chunk in enumerate(batch):
                if j >= len(resp.items):
                    failed += 1
                    continue
                item = resp.items[j]
                vec = item.embedding
                try:
                    self._validate_vector_dimensions(vec, dims)
                except ValidationServiceError as exc:
                    self._set_chunk_failed(chunk, str(exc))
                    failed += 1
                    errors.append({"chunk_id": str(chunk.id), "error": str(exc)})
                    continue

                chunk.embedding = vec
                chunk.embedding_status = "completed"
                chunk.embedding_provider = resp.provider
                chunk.embedding_model = resp.model
                chunk.embedding_dimensions = resp.dimensions
                chunk.embedding_created_at = datetime.now(timezone.utc)
                chunk.embedding_error = None
                if item.token_count is not None and chunk.token_count is None:
                    chunk.token_count = item.token_count
                embedded += 1

            self._commit()

        status_str = "completed" if failed == 0 else ("partial" if embedded > 0 else "failed")
        return BulkChunkEmbeddingResponse(
            target_type="book",
            target_id=book_id,
            total_candidates=total,
            embedded_count=embedded,
            skipped_count=skipped,
            failed_count=failed,
            provider=last_provider,
            model=last_model,
            dimensions=dims,
            status=status_str,
            errors=errors,
        )
