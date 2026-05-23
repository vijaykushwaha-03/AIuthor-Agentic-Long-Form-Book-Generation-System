"""
AIuthor Backend — Semantic Retrieval Service (Module 6.0B).

Retrieves DocumentChunk records by vector similarity.

Two retrieval modes:
  A. PostgreSQL + pgvector: cosine distance ORDER BY clause (fast, indexed).
  B. SQLite / test DB or pgvector unavailable: Python cosine similarity fallback.

Always uses mock embedding provider in tests (injected via constructor).
Never calls Gemini/OpenAI in tests.
"""
from __future__ import annotations

import logging
import math
from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.pgvector_check import is_pgvector_available
from app.embeddings.factory import get_embedding_provider
from app.embeddings.schemas import EmbeddingRequest
from app.models.document import DocumentChunk, SourceDocument
from app.schemas.rag import RetrievalResultItem, SemanticRetrievalRequest, SemanticRetrievalResponse
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import ValidationServiceError

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two float vectors in pure Python.
    Returns a value in [-1.0, 1.0]; 1.0 = identical direction.
    Returns 0.0 if either vector has zero magnitude.
    """
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class SemanticRetrievalService:
    """
    Implements semantic (vector) retrieval for DocumentChunk records.

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

    def _get_service_for_request(self, provider_name: str | None) -> EmbeddingService:
        if provider_name:
            p = get_embedding_provider(provider_name)
            return EmbeddingService(provider=p)
        return self.embedding_service

    def semantic_retrieve(
        self,
        request: SemanticRetrievalRequest,
    ) -> SemanticRetrievalResponse:
        """
        Embed the query text and return the top-K most similar DocumentChunks.

        Strategy:
          - If connected to PostgreSQL and pgvector is available:
            Use native cosine-distance ORDER BY (<=> operator).
          - Otherwise (SQLite / pgvector not installed):
            Fetch all candidate vectors and rank with Python cosine similarity.

        Args:
            request: SemanticRetrievalRequest with query text and filters.

        Returns:
            SemanticRetrievalResponse with ranked results.
        """
        dims = self._settings.RAG_VECTOR_DIMENSIONS
        svc = self._get_service_for_request(request.provider)

        # ── 1. Embed the query ────────────────────────────────────────────────
        try:
            embed_req = EmbeddingRequest(
                texts=[request.query],
                dimensions=dims,
                metadata={"retrieval_type": "semantic_query"},
            )
            embed_resp = svc.embed_texts(embed_req)
        except Exception as exc:
            raise ValidationServiceError(
                f"Failed to embed query text: {exc}"
            ) from exc

        if not embed_resp.items:
            raise ValidationServiceError("Embedding provider returned no items for query.")

        query_vector = embed_resp.items[0].embedding

        if len(query_vector) != dims:
            raise ValidationServiceError(
                f"Query vector dimension mismatch: expected {dims}, got {len(query_vector)}."
            )

        # ── 2. Build base ORM filter ──────────────────────────────────────────
        base_query = (
            self.db.query(DocumentChunk, SourceDocument)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
            .filter(
                DocumentChunk.embedding_status == "completed",
                DocumentChunk.embedding_dimensions == dims,
                DocumentChunk.embedding != None,  # noqa: E711
            )
        )
        if request.book_id is not None:
            base_query = base_query.filter(DocumentChunk.book_id == request.book_id)
        if request.document_id is not None:
            base_query = base_query.filter(DocumentChunk.document_id == request.document_id)

        # ── 3. Detect dialect and choose retrieval strategy ───────────────────
        pgvector_used = False
        results: list[RetrievalResultItem] = []

        try:
            is_pg = self.db.bind.dialect.name == "postgresql"  # type: ignore[union-attr]
        except Exception:
            is_pg = False

        pgvector_available = False
        if is_pg:
            pgvector_available = is_pgvector_available(self.db)
            if not pgvector_available and not self._settings.ALLOW_PGVECTOR_FALLBACK:
                from app.services.exceptions import ServiceError
                raise ServiceError(
                    message="pgvector extension is missing on PostgreSQL server and allow_pgvector_fallback is false",
                    code="pgvector_missing"
                )

        if is_pg and pgvector_available:
            # Strategy A: native pgvector cosine distance
            try:
                vec_literal = "[" + ",".join(str(v) for v in query_vector) + "]"
                rows = (
                    base_query
                    .order_by(
                        sa_text(f"embedding <=> '{vec_literal}'::vector")
                    )
                    .limit(request.top_k)
                    .all()
                )
                for chunk, doc in rows:
                    # Convert cosine distance → similarity: sim = 1 - dist
                    # We compute approximate similarity from Python as well for the score.
                    stored_vec = chunk.embedding
                    stored_vec_list = None
                    if stored_vec is not None:
                        if hasattr(stored_vec, "tolist"):
                            stored_vec_list = stored_vec.tolist()
                        elif isinstance(stored_vec, (list, tuple)):
                            stored_vec_list = list(stored_vec)
                    
                    if stored_vec_list:
                        score = _cosine_similarity(query_vector, stored_vec_list)
                    else:
                        score = 0.0

                    results.append(
                        RetrievalResultItem(
                            chunk_id=chunk.id,
                            document_id=chunk.document_id,
                            book_id=chunk.book_id,
                            chunk_text=chunk.chunk_text if request.include_raw_text else None,
                            score=max(0.0, score),
                            source_title=doc.title,
                            source_url=doc.source_url,
                            metadata={
                                "embedding_provider": chunk.embedding_provider,
                                "embedding_model": chunk.embedding_model,
                                "embedding_dimensions": chunk.embedding_dimensions,
                            },
                        )
                    )
                pgvector_used = True
            except Exception as exc:
                logger.error("pgvector query failed: %s", exc)
                if not self._settings.ALLOW_PGVECTOR_FALLBACK:
                    from app.services.exceptions import ServiceError
                    raise ServiceError(
                        message=f"pgvector query failed and pgvector fallback is disabled: {exc}",
                        code="pgvector_query_failed"
                    )
                pgvector_used = False
                results = []

        if not pgvector_used:
            # Strategy B: Python cosine similarity fallback
            all_rows = base_query.all()
            scored: list[tuple[float, DocumentChunk, SourceDocument]] = []
            for chunk, doc in all_rows:
                stored_vec = chunk.embedding
                stored_vec_list = None
                if stored_vec is not None:
                    if hasattr(stored_vec, "tolist"):
                        stored_vec_list = stored_vec.tolist()
                    elif isinstance(stored_vec, (list, tuple)):
                        stored_vec_list = list(stored_vec)
                
                if not stored_vec_list:
                    continue
                score = _cosine_similarity(query_vector, stored_vec_list)
                scored.append((score, chunk, doc))

            scored.sort(key=lambda t: t[0], reverse=True)

            for score, chunk, doc in scored[: request.top_k]:
                results.append(
                    RetrievalResultItem(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        book_id=chunk.book_id,
                        chunk_text=chunk.chunk_text if request.include_raw_text else None,
                        score=max(0.0, score),
                        source_title=doc.title,
                        source_url=doc.source_url,
                        metadata={
                            "embedding_provider": chunk.embedding_provider,
                            "embedding_model": chunk.embedding_model,
                            "embedding_dimensions": chunk.embedding_dimensions,
                        },
                    )
                )

        return SemanticRetrievalResponse(
            query=request.query,
            provider=embed_resp.provider,
            model=embed_resp.model,
            dimensions=embed_resp.dimensions,
            results=results,
            retrieval_mode="semantic",
            pgvector_used=pgvector_used,
        )
