"""
AIuthor Backend — RAG Context Pack Service (Module 6.1).

Builds agent-ready context packs by calling the hybrid retriever and formatting
results with deterministic citation tags and size-boundary truncation.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.book import BookProject
from app.models.chapter import Chapter
from app.models.document import DocumentChunk
from app.schemas.rag import (
    ContextPackRequest,
    ContextPackResponse,
    HybridRetrievalRequest,
    ContextChunk,
)
from app.services.exceptions import NotFoundError, ValidationServiceError
from app.services.hybrid_retrieval_service import HybridRetrievalService

logger = logging.getLogger(__name__)


class ContextPackService:
    """
    Builds structured, citation-annotated context blocks for AIuthor agents.
    """

    def __init__(
        self,
        db: Session,
        hybrid_service: HybridRetrievalService | None = None,
    ) -> None:
        self.db = db
        self.hybrid_service = hybrid_service or HybridRetrievalService(db)

    def build_context_pack(
        self,
        request: ContextPackRequest,
    ) -> ContextPackResponse:
        """
        Retrieves hybrid RAG matches and formats them into a single, cohesive
        context block for agents, adhering to strict size bounds.
        """
        # 1. Verify BookProject exists
        book = self.db.get(BookProject, request.book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(request.book_id)},
            )

        # 2. If chapter_id is provided, verify it exists and belongs to the book
        if request.chapter_id is not None:
            chapter = self.db.get(Chapter, request.chapter_id)
            if chapter is None:
                raise NotFoundError(
                    message="Chapter not found",
                    code="chapter_not_found",
                    details={"chapter_id": str(request.chapter_id)},
                )
            if chapter.book_id != request.book_id:
                raise ValidationServiceError(
                    message="Chapter does not belong to the specified book project",
                    code="chapter_book_mismatch",
                    details={
                        "chapter_id": str(request.chapter_id),
                        "book_id": str(request.book_id),
                    },
                )

        # 3. Run Hybrid Retrieval
        hybrid_req = HybridRetrievalRequest(
            query=request.query,
            book_id=request.book_id,
            document_id=request.document_id,
            top_k=request.max_chunks,
            provider=request.provider,
            include_raw_text=True,
        )
        hybrid_resp = self.hybrid_service.hybrid_retrieve(hybrid_req)

        # 4. Convert results into ContextChunk list
        chunks = []
        citations_by_chunk_id = {c.chunk_id: c for c in hybrid_resp.citations}

        # Query DocumentChunk records to retrieve token_count accurately
        chunk_ids = [res.chunk_id for res in hybrid_resp.results]
        db_chunks = {}
        if chunk_ids:
            db_chunks = {
                c.id: c for c in self.db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
            }

        for res in hybrid_resp.results:
            citation = citations_by_chunk_id.get(res.chunk_id)
            retrieval_mode = citation.retrieval_mode if citation else "hybrid"
            citation_id = citation.citation_id if citation else "C?"

            db_chunk = db_chunks.get(res.chunk_id)
            token_count = db_chunk.token_count if db_chunk else None

            # Copy metadata dictionary to prevent mutating the original chunk metadata
            chunk_metadata = dict(res.metadata) if res.metadata else {}

            chunks.append(
                ContextChunk(
                    citation_id=citation_id,
                    chunk_id=res.chunk_id,
                    document_id=res.document_id,
                    text=res.chunk_text or "",
                    score=res.score,
                    retrieval_mode=retrieval_mode,
                    token_count=token_count,
                    metadata=chunk_metadata,
                )
            )

        # 5. Build context_text and respect max_context_chars limit
        context_blocks = []
        included_chunks = []
        truncated = False

        for c in chunks:
            citation = citations_by_chunk_id.get(c.chunk_id)
            source_title = citation.source_title if (citation and citation.source_title) else str(c.document_id)
            chunk_index = citation.chunk_index if citation else 0

            # Stable and agent-readable format:
            # [C1] Source: <source_title or document_id>, Chunk <chunk_index>
            # <chunk text>
            block_header = f"[{c.citation_id}] Source: {source_title}, Chunk {chunk_index}\n"
            block_body = c.text
            block_text = f"{block_header}{block_body}"

            current_separator = "\n\n" if context_blocks else ""
            proposed_addition = f"{current_separator}{block_text}"

            # Compute length of accumulated blocks so far
            current_accumulated_len = sum(len(b) for b in context_blocks)
            if context_blocks:
                current_accumulated_len += (len(context_blocks) - 1) * 2  # Separator lengths

            if current_accumulated_len + len(proposed_addition) <= request.max_context_chars:
                context_blocks.append(block_text)
                included_chunks.append(c)
            else:
                # If we have no blocks yet, the first chunk alone exceeds the limit. Truncate it.
                if not context_blocks:
                    available_chars = request.max_context_chars - len(block_header)
                    if available_chars > 0:
                        truncated_body = block_body[:available_chars]
                        truncated_block = f"{block_header}{truncated_body}"
                        context_blocks.append(truncated_block)

                        c.text = truncated_body
                        if c.metadata is None:
                            c.metadata = {}
                        c.metadata["truncated"] = True

                        included_chunks.append(c)
                        truncated = True
                else:
                    # We have at least one block, so stop adding more to avoid cutting a chunk mid-text.
                    pass
                break

        context_text = "\n\n".join(context_blocks)
        total_context_chars = len(context_text)

        # Include specific required metadata layout
        response_metadata = {
            "max_chunks": request.max_chunks,
            "max_context_chars": request.max_context_chars,
            "include_memory_hints": request.include_memory_hints,
            "memory_hints_included": False,
            "note": "Memory hints will be enriched later by agent workflow modules",
            "truncated": truncated,
        }

        # Filter the citation list to match only those chunks that were actually included in the final context block
        included_chunk_ids = {c.chunk_id for c in included_chunks}
        filtered_citations = [
            citation for citation in hybrid_resp.citations if citation.chunk_id in included_chunk_ids
        ]

        # Re-index citation_id consecutively if some chunks were left out
        final_citations = []
        for index, old_cit in enumerate(filtered_citations):
            # Find the corresponding context chunk and update its citation_id to keep it aligned
            new_id = f"C{index + 1}"
            for c in included_chunks:
                if c.chunk_id == old_cit.chunk_id:
                    c.citation_id = new_id

            final_citations.append(
                old_cit.model_copy(update={"citation_id": new_id})
            )

        return ContextPackResponse(
            query=request.query,
            book_id=request.book_id,
            chapter_id=request.chapter_id,
            context_text=context_text,
            chunks=included_chunks,
            citations=final_citations,
            total_chunks=len(included_chunks),
            total_context_chars=total_context_chars,
            retrieval_mode="hybrid_context_pack",
            metadata=response_metadata,
        )
