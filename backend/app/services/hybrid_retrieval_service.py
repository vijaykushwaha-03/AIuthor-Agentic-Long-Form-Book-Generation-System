"""
AIuthor Backend — Hybrid Retrieval Service (Module 6.1).

Combines lexical (keyword) retrieval and semantic (vector) retrieval,
performing score merging, deduplication, and source attribution.
"""
from __future__ import annotations

import logging
from uuid import UUID
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk, SourceDocument
from app.schemas.rag import (
    HybridRetrievalRequest,
    HybridRetrievalResponse,
    SemanticRetrievalRequest,
    RetrievalResultItem,
    CitationItem,
)
from app.services.semantic_retrieval_service import SemanticRetrievalService

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    """
    Combines lexical and semantic retrieval methodologies to retrieve
    high-quality RAG contexts for book projects.
    """

    def __init__(
        self,
        db: Session,
        semantic_service: SemanticRetrievalService | None = None,
    ) -> None:
        self.db = db
        self.semantic_service = semantic_service or SemanticRetrievalService(db)

    def hybrid_retrieve(
        self,
        request: HybridRetrievalRequest,
    ) -> HybridRetrievalResponse:
        """
        Retrieves relevant chunks using both vector similarity and lexical matching,
        merging, deduplicating, and scoring them accordingly.
        """
        # 1. Run semantic retrieval with increased top_k for a better merge pool
        semantic_top_k = request.top_k * 2
        sem_req = SemanticRetrievalRequest(
            query=request.query,
            book_id=request.book_id,
            document_id=request.document_id,
            top_k=semantic_top_k,
            provider=request.provider,
            include_raw_text=request.include_raw_text,
        )

        try:
            sem_resp = self.semantic_service.semantic_retrieve(sem_req)
            semantic_results = sem_resp.results
        except Exception as exc:
            logger.warning("Semantic retrieval failed in hybrid flow: %s. Proceeding with lexical-only.", exc)
            semantic_results = []

        semantic_by_id = {item.chunk_id: item for item in semantic_results}

        # 2. Run lexical retrieval locally
        lexical_limit = request.top_k * 2
        lexical_results = self.lexical_retrieve_chunks(
            query=request.query,
            book_id=request.book_id,
            document_id=request.document_id,
            limit=lexical_limit,
        )
        lexical_by_id = {res["chunk"].id: res for res in lexical_results}

        # 3. Merge both result lists
        all_chunk_ids = set(semantic_by_id.keys()) | set(lexical_by_id.keys())

        # Pre-load missing chunks and documents in one batch query to avoid N+1 queries
        missing_ids = [cid for cid in all_chunk_ids if cid not in lexical_by_id]
        loaded_chunks = {}
        if missing_ids:
            rows = (
                self.db.query(DocumentChunk, SourceDocument)
                .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
                .filter(DocumentChunk.id.in_(missing_ids))
                .all()
            )
            for chunk, doc in rows:
                loaded_chunks[chunk.id] = (chunk, doc)

        # Merge, calculate combined scores, and determine retrieval modes
        candidates = []
        for chunk_id in all_chunk_ids:
            sem_item = semantic_by_id.get(chunk_id)
            lex_item = lexical_by_id.get(chunk_id)

            if lex_item:
                chunk = lex_item["chunk"]
                doc = lex_item["doc"]
            else:
                chunk, doc = loaded_chunks.get(chunk_id, (None, None))

            if chunk is None:
                continue

            sem_score = sem_item.score if (sem_item and sem_item.score is not None) else 0.0
            lex_score = lex_item["score"] if lex_item else 0.0

            combined_score = (
                sem_score * request.semantic_weight +
                lex_score * request.lexical_weight
            )

            # Discard zero or negative score candidates to avoid returning unrelated chunks
            if combined_score <= 0.0:
                continue

            # Filter by min_score if provided
            if request.min_score is not None and combined_score < request.min_score:
                continue

            if sem_item is not None and lex_item is not None:
                retrieval_mode = "hybrid"
            elif sem_item is not None:
                retrieval_mode = "semantic"
            else:
                retrieval_mode = "lexical"

            candidates.append({
                "chunk": chunk,
                "doc": doc,
                "score": combined_score,
                "retrieval_mode": retrieval_mode,
            })

        # Sort: combined score descending, tie-break by chunk_index ascending
        candidates.sort(key=lambda x: (-x["score"], x["chunk"].chunk_index))

        # Limit to requested top_k
        ranked = candidates[:request.top_k]

        # 4. Build response schemas
        results = []
        for item in ranked:
            chunk = item["chunk"]
            doc = item["doc"]
            results.append(
                RetrievalResultItem(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    book_id=chunk.book_id,
                    chunk_text=chunk.chunk_text if request.include_raw_text else None,
                    score=item["score"],
                    source_title=doc.title if doc else None,
                    source_url=doc.source_url if doc else None,
                    metadata=chunk.chunk_metadata,
                )
            )

        citations = self.build_citations(ranked)

        # Count modes in final limited set
        semantic_count = sum(1 for item in ranked if item["retrieval_mode"] == "semantic")
        lexical_count = sum(1 for item in ranked if item["retrieval_mode"] == "lexical")
        merged_count = sum(1 for item in ranked if item["retrieval_mode"] == "hybrid")

        return HybridRetrievalResponse(
            query=request.query,
            results=results,
            citations=citations,
            retrieval_mode="hybrid",
            semantic_count=semantic_count,
            lexical_count=lexical_count,
            merged_count=merged_count,
        )

    def lexical_retrieve_chunks(
        self,
        query: str,
        book_id: UUID | None = None,
        document_id: UUID | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """
        Query DocumentChunk rows using LIKE/ILIKE fallback compatible with SQLite.
        Filters by book_id and document_id, then ranks using keyword exact phrase
        and term frequency overlap.
        """
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if not terms:
            return []

        base_q = (
            self.db.query(DocumentChunk, SourceDocument)
            .join(SourceDocument, DocumentChunk.document_id == SourceDocument.id)
        )

        if book_id is not None:
            base_q = base_q.filter(DocumentChunk.book_id == book_id)
        if document_id is not None:
            base_q = base_q.filter(DocumentChunk.document_id == document_id)

        # Filter: chunk contains at least one of the query terms
        base_q = base_q.filter(
            or_(*(DocumentChunk.chunk_text.ilike(f"%{term}%") for term in terms))
        )

        candidates = base_q.all()
        results = []

        query_lower = query.lower()
        for chunk, doc in candidates:
            text_lower = chunk.chunk_text.lower()
            if query_lower in text_lower:
                score = 1.0
                matched_terms = terms
            else:
                matched_terms = [t for t in terms if t in text_lower]
                score = len(matched_terms) / len(terms) if terms else 0.0

            if score > 0.0:
                results.append({
                    "chunk": chunk,
                    "doc": doc,
                    "score": score,
                    "matched_terms": matched_terms,
                })

        # Sort: score descending, tie-break by chunk_index ascending
        results.sort(key=lambda x: (-x["score"], x["chunk"].chunk_index))

        return results[:limit]

    def build_citations(
        self,
        ranked_items: list[dict],
    ) -> list[CitationItem]:
        """
        Builds a deterministic sequence of CitationItems marked C1, C2, C3...
        based on the ranked ordering of chunks.
        """
        citations = []
        for index, item in enumerate(ranked_items):
            chunk = item["chunk"]
            doc = item["doc"]
            citation_id = f"C{index + 1}"
            citations.append(
                CitationItem(
                    citation_id=citation_id,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    source_title=doc.title if doc else None,
                    source_type=doc.source_type if doc else None,
                    source_url=doc.source_url if doc else None,
                    chunk_index=chunk.chunk_index,
                    score=item["score"],
                    retrieval_mode=item["retrieval_mode"],
                    metadata=chunk.chunk_metadata,
                )
            )
        return citations
