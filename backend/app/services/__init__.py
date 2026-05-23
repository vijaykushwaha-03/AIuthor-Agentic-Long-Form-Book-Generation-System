"""
AIuthor Backend — Services Package.

Exports service classes and exceptions for use by API route layers.
"""
from __future__ import annotations

from app.services.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)
from app.services.book_service import BookProjectService
from app.services.run_service import BookRunService
from app.services.chapter_service import ChapterService
from app.services.section_service import BookSectionService
from app.services.rag_service import SourceDocumentService, DocumentChunkService
from app.services.memory_service import MemoryService
from app.services.observability_service import ObservabilityService
from app.services.eval_service import EvalService
from app.services.export_service import ExportService
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService
from app.services.chunk_embedding_service import ChunkEmbeddingService
from app.services.semantic_retrieval_service import SemanticRetrievalService
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.context_pack_service import ContextPackService

__all__ = [
    "ServiceError",
    "NotFoundError",
    "ValidationServiceError",
    "ConflictError",
    "BookProjectService",
    "BookRunService",
    "ChapterService",
    "BookSectionService",
    "SourceDocumentService",
    "DocumentChunkService",
    "MemoryService",
    "ObservabilityService",
    "EvalService",
    "ExportService",
    "LLMService",
    "EmbeddingService",
    "ChunkEmbeddingService",
    "SemanticRetrievalService",
    "HybridRetrievalService",
    "ContextPackService",
]


