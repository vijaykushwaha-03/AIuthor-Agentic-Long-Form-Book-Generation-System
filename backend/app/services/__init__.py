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
from app.services.agent_execution_service import AgentExecutionService
from app.services.workflow_execution_service import WorkflowExecutionService
from app.services.workflow_observability_service import WorkflowObservabilityService
from app.services.bookrun_workflow_service import BookRunWorkflowService
from app.services.chapter_generation_service import ChapterGenerationService
from app.services.chapter_self_healing_service import ChapterSelfHealingService
from app.services.memory_extraction_service import MemoryExtractionService
from app.services.continuity_pack_service import ContinuityPackService
from app.services.book_assembler_service import BookAssemblerService
from app.services.document_export_service import DocumentExportService
from app.services.prompt_dossier_service import PromptDossierService
from app.services.evaluation_report_service import EvaluationReportService
from app.services.delivery_bundle_service import DeliveryBundleService

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
    "AgentExecutionService",
    "WorkflowExecutionService",
    "WorkflowObservabilityService",
    "BookRunWorkflowService",
    "ChapterGenerationService",
    "ChapterSelfHealingService",
    "MemoryExtractionService",
    "ContinuityPackService",
    "BookAssemblerService",
    "DocumentExportService",
    "PromptDossierService",
    "EvaluationReportService",
    "DeliveryBundleService",
]




