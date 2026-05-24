"""
AIuthor Backend — Workflow Pydantic Schemas (Module 7.1A).
"""
from __future__ import annotations

from uuid import UUID
from pydantic import Field, field_validator, model_validator
from app.schemas.base import BaseSchema


class WorkflowInput(BaseSchema):
    """
    Input model required to invoke any AIuthor workflow pipeline.
    """
    workflow_name: str = "mini_book_pipeline"
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    topic: str = Field(..., min_length=1)
    genre: str | None = None
    reader_profile: str | None = None
    tone: str | None = None
    task: str | None = None
    context_pack: dict | None = None
    memory_context: dict | None = None
    payload: dict | None = None
    metadata: dict | None = None

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v not in ["mini_book_pipeline", "full_agent_pipeline"]:
            from app.workflows.exceptions import WorkflowConfigurationError
            raise WorkflowConfigurationError(
                message=f"Workflow '{v}' is not registered or supported.",
                workflow_name=v,
            )
        return v


class WorkflowStepOutput(BaseSchema):
    """
    Output from a single agent node execution within the workflow.
    """
    step_name: str
    agent_name: str
    status: str
    content: str | None = None
    structured_output: dict | None = None
    error_message: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict | None = None


class WorkflowOutput(BaseSchema):
    """
    Final output returned after a complete workflow execution.
    """
    workflow_name: str
    status: str
    final_content: str | None = None
    steps: list[WorkflowStepOutput] = Field(default_factory=list)
    error_message: str | None = None
    metadata: dict | None = None


class WorkflowInfo(BaseSchema):
    """
    Metadata descriptor summarizing a registered workflow's capabilities.
    """
    workflow_name: str
    display_name: str
    description: str
    nodes: list[str] = Field(default_factory=list)
    enabled: bool = True
    supports_mock: bool = True
    supports_real_dev: bool = True


class WorkflowTraceRequest(BaseSchema):
    """
    Input model required to invoke any AIuthor workflow pipeline with trace logging enabled.
    """
    workflow_name: str = "mini_book_pipeline"
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    topic: str = Field(..., min_length=1)
    genre: str | None = None
    reader_profile: str | None = None
    tone: str | None = None
    context_pack: dict | None = None
    memory_context: dict | None = None
    payload: dict | None = None
    metadata: dict | None = None
    persist_traces: bool = True

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v not in ["mini_book_pipeline", "full_agent_pipeline"]:
            from app.workflows.exceptions import WorkflowConfigurationError
            raise WorkflowConfigurationError(
                message=f"Workflow '{v}' is not registered or supported.",
                workflow_name=v,
            )
        return v


class WorkflowTraceStep(BaseSchema):
    """
    Individual step execution trace log entry recorded in a workflow run.
    """
    step_name: str
    agent_name: str
    status: str
    trace_id: UUID | None = None
    prompt_log_id: UUID | None = None
    token_cost_id: UUID | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    error_message: str | None = None
    content_preview: str | None = None
    metadata: dict | None = None


class WorkflowTraceResponse(BaseSchema):
    """
    Aggregated response returned by the traced workflow execution engine.
    """
    workflow_name: str
    status: str
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    execution_mode: str
    final_content: str | None = None
    steps: list[WorkflowTraceStep] = Field(default_factory=list)
    trace_bundle: dict | None = None
    error_message: str | None = None
    metadata: dict | None = None


class BookRunWorkflowRequest(BaseSchema):
    """
    Request model for triggering a workflow execution against real BookProject/BookRun records.
    """
    book_id: UUID | None = None
    run_id: UUID | None = None
    chapter_id: UUID | None = None
    workflow_name: str = "full_agent_pipeline"
    execution_mode: str = "mock"
    traced: bool = True
    persist_traces: bool = True
    build_context_pack: bool = True
    context_query: str | None = None
    max_context_chunks: int = Field(8, ge=1, le=30)
    max_context_chars: int = Field(12000, ge=1000, le=50000)
    payload: dict | None = None
    metadata: dict | None = None

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v not in ["mini_book_pipeline", "full_agent_pipeline"]:
            raise ValueError(f"Workflow '{v}' is not registered or supported.")
        return v

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ["mock", "real_dev"]:
            raise ValueError(f"Execution mode '{v}' is not supported.")
        return v

    @field_validator("max_context_chunks")
    @classmethod
    def validate_max_context_chunks(cls, v: int) -> int:
        if not (1 <= v <= 30):
            raise ValueError("max_context_chunks must be between 1 and 30")
        return v

    @field_validator("max_context_chars")
    @classmethod
    def validate_max_context_chars(cls, v: int) -> int:
        if not (1000 <= v <= 50000):
            raise ValueError("max_context_chars must be between 1000 and 50000")
        return v


class BookRunWorkflowResponse(BaseSchema):
    """
    Response model returned after a DB-backed BookRun workflow execution.
    """
    book_id: UUID
    run_id: UUID
    chapter_id: UUID | None = None
    workflow_name: str
    execution_mode: str
    traced: bool
    status: str
    workflow_output: dict
    context_pack: dict | None = None
    trace_bundle: dict | None = None
    metadata: dict | None = None


class ChapterGenerationRequest(BaseSchema):
    """
    Request model for triggering sequential chapter generation loops.
    """
    book_id: UUID | None = None
    run_id: UUID | None = None
    chapter_ids: list[UUID] | None = None
    chapter_numbers: list[int] | None = None
    workflow_name: str = "full_agent_pipeline"
    execution_mode: str = "mock"
    traced: bool = True
    persist_traces: bool = True
    build_context_pack: bool = True
    persist_chapter_content: bool = True
    overwrite_existing: bool = False
    max_chapters: int | None = Field(None, ge=1, le=50)
    max_context_chunks: int = Field(8, ge=1, le=30)
    max_context_chars: int = Field(12000, ge=1000, le=50000)
    context_query_template: str | None = None
    payload: dict | None = None
    metadata: dict | None = None

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v != "full_agent_pipeline":
            raise ValueError("workflow_name must be 'full_agent_pipeline'")
        return v

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ["mock", "real_dev"]:
            raise ValueError(f"Execution mode '{v}' is not supported.")
        return v

    @field_validator("chapter_numbers")
    @classmethod
    def validate_chapter_numbers(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for num in v:
                if num < 1:
                    raise ValueError("chapter_numbers must be positive integers")
        return v


class ChapterGenerationItem(BaseSchema):
    """
    Status of an individual chapter run within the generation loop.
    """
    chapter_id: UUID
    chapter_number: int | None = None
    title: str | None = None
    status: str
    workflow_status: str
    content_preview: str | None = None
    content_chars: int | None = None
    trace_count: int = 0
    error_message: str | None = None
    metadata: dict | None = None


class ChapterGenerationResponse(BaseSchema):
    """
    Aggregated response returned by the chapter generation loop service.
    """
    book_id: UUID
    run_id: UUID
    workflow_name: str
    execution_mode: str
    traced: bool
    total_requested: int
    completed_count: int
    failed_count: int
    skipped_count: int
    chapters: list[ChapterGenerationItem]
    status: str
    trace_bundle: dict | None = None
    metadata: dict | None = None


class InsertChapterRepairRequest(BaseSchema):
    """
    Request schema for inserting a chapter and triggering self-healing repair.
    """
    book_id: UUID
    run_id: UUID | None = None
    insert_at_chapter_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    summary: str | None = None
    generate_content: bool = True
    workflow_name: str = "full_agent_pipeline"
    execution_mode: str = "mock"
    traced: bool = True
    persist_traces: bool = True
    build_context_pack: bool = True
    repair_toc: bool = True
    repair_callbacks: bool = True
    repair_glossary: bool = True
    repair_back_matter: bool = True
    overwrite_existing_repair: bool = True
    context_query: str | None = None
    max_context_chunks: int = Field(8, ge=1, le=30)
    max_context_chars: int = Field(12000, ge=1000, le=50000)
    payload: dict | None = None
    metadata: dict | None = None

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v != "full_agent_pipeline":
            raise ValueError("workflow_name must be 'full_agent_pipeline'")
        return v

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ["mock", "real_dev"]:
            raise ValueError(f"Execution mode '{v}' is not supported.")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title cannot be empty or only whitespace")
        return v.strip()


class StructureRepairItem(BaseSchema):
    """
    Log of a single self-healing action executed for the book.
    """
    item_type: str
    item_id: UUID | None = None
    status: str
    message: str
    before_value: dict | str | int | None = None
    after_value: dict | str | int | None = None
    metadata: dict | None = None


class InsertChapterRepairResponse(BaseSchema):
    """
    Response schema summarizing the insert and repair execution.
    """
    book_id: UUID
    run_id: UUID
    inserted_chapter_id: UUID
    inserted_chapter_number: int
    workflow_name: str
    execution_mode: str
    status: str
    generated_content_preview: str | None = None
    repair_items: list[StructureRepairItem] = Field(default_factory=list)
    affected_chapter_ids: list[UUID] = Field(default_factory=list)
    toc_repaired: bool = False
    callbacks_repaired: bool = False
    glossary_repaired: bool = False
    back_matter_repaired: bool = False
    trace_bundle: dict | None = None
    metadata: dict | None = None


# ── Memory Extraction Schemas ────────────────────────────────────────────────

class MemoryExtractionRequest(BaseSchema):
    """
    Request model for memory extraction service.
    """
    book_id: UUID
    run_id: UUID | None = None
    chapter_id: UUID | None = None
    source_type: str = "text"
    source_text: str | None = None
    workflow_output: dict | None = None
    trace_bundle: dict | None = None
    execution_mode: str = "mock"
    persist_memory: bool = True
    include_facts: bool = True
    include_concepts: bool = True
    include_characters: bool = True
    include_callbacks: bool = True
    include_tone: bool = True
    include_decisions: bool = True
    overwrite_existing: bool = False
    payload: dict | None = None
    metadata: dict | None = None

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        if v not in ["mock", "real_dev"]:
            raise ValueError("execution_mode must be 'mock' or 'real_dev'")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in ["text", "chapter", "workflow_output", "trace_bundle"]:
            raise ValueError("source_type must be one of: text, chapter, workflow_output, trace_bundle")
        return v

    @model_validator(mode="after")
    def validate_sources(self) -> MemoryExtractionRequest:
        if not (self.source_text or self.workflow_output or self.trace_bundle or self.chapter_id):
            raise ValueError("At least one of source_text, workflow_output, trace_bundle, or chapter_id must be provided.")
        if self.source_text is not None and not self.source_text.strip():
            raise ValueError("source_text must not be blank if provided.")
        return self


class MemoryCandidate(BaseSchema):
    """
    Candidate memory record extracted from source text.
    """
    memory_type: str
    key: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    source_agent: str | None = None
    source_citation_id: str | None = None
    chapter_id: UUID | None = None
    metadata: dict | None = None

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        valid_types = ["fact", "concept", "character", "callback", "tone", "decision"]
        if v not in valid_types:
            raise ValueError(f"memory_type must be one of {valid_types}")
        return v


class MemoryWriteResult(BaseSchema):
    """
    Result of writing a single candidate memory record to the DB.
    """
    memory_type: str
    key: str
    status: str
    record_id: UUID | None = None
    skipped_reason: str | None = None
    error_message: str | None = None
    metadata: dict | None = None


class MemoryExtractionResponse(BaseSchema):
    """
    Response model for memory extraction runs.
    """
    book_id: UUID
    run_id: UUID | None = None
    chapter_id: UUID | None = None
    source_type: str
    execution_mode: str
    status: str
    candidates: list[MemoryCandidate]
    write_results: list[MemoryWriteResult]
    total_candidates: int
    written_count: int
    skipped_count: int
    failed_count: int
    metadata: dict | None = None


class ContinuityPackRequest(BaseSchema):
    """
    Request model for building a continuity pack document.
    """
    book_id: UUID
    chapter_id: UUID | None = None
    include_facts: bool = True
    include_concepts: bool = True
    include_characters: bool = True
    include_callbacks: bool = True
    include_tone: bool = True
    include_decisions: bool = True
    max_items_per_type: int = Field(20, ge=1, le=100)
    max_chars: int = Field(12000, ge=1000, le=50000)
    metadata: dict | None = None


class ContinuityPackResponse(BaseSchema):
    """
    Response model containing continuity context for agents.
    """
    book_id: UUID
    chapter_id: UUID | None = None
    continuity_text: str
    facts: list[dict] = Field(default_factory=list)
    concepts: list[dict] = Field(default_factory=list)
    characters: list[dict] = Field(default_factory=list)
    callbacks: list[dict] = Field(default_factory=list)
    tone_fingerprints: list[dict] = Field(default_factory=list)
    decisions: list[dict] = Field(default_factory=list)
    total_items: int
    total_chars: int
    metadata: dict | None = None


# ── Book Assembly & Export Schemas ───────────────────────────────────────────

class BookAssemblyRequest(BaseSchema):
    """
    Request model for manuscript assembly.
    """
    book_id: UUID
    run_id: UUID | None = None
    include_front_matter: bool = True
    include_back_matter: bool = True
    include_toc: bool = True
    include_glossary: bool = True
    include_bibliography: bool = True
    include_memory_notes: bool = False
    prefer_final_text: bool = True
    metadata: dict | None = None


class AssembledChapter(BaseSchema):
    """
    A single assembled chapter included in the final book structure.
    """
    chapter_id: UUID
    chapter_number: int
    title: str
    content: str
    source_field: str
    word_count: int
    metadata: dict | None = None


class BookAssemblyResponse(BaseSchema):
    """
    Complete structured response summarizing the assembled book.
    """
    book_id: UUID
    run_id: UUID | None = None
    title: str
    subtitle: str | None = None
    author: str | None = None
    front_matter: list[dict]
    chapters: list[AssembledChapter]
    back_matter: list[dict]
    toc: list[dict]
    glossary: list[dict]
    bibliography: list[dict]
    total_chapters: int
    total_words: int
    metadata: dict | None = None


class BookExportRequest(BaseSchema):
    """
    Request model for turning the assembled book into real files.
    """
    book_id: UUID
    run_id: UUID | None = None
    export_types: list[str] = Field(default_factory=lambda: ["docx", "pdf"])
    include_front_matter: bool = True
    include_back_matter: bool = True
    include_toc: bool = True
    include_glossary: bool = True
    include_bibliography: bool = True
    include_memory_notes: bool = False
    overwrite_existing: bool = True
    prefer_final_text: bool = True
    metadata: dict | None = None


    @field_validator("export_types")
    @classmethod
    def validate_export_types(cls, v: list[str]) -> list[str]:
        if not v or len(v) < 1:
            raise ValueError("export_types must contain at least 1 item")
        for t in v:
            if t not in ["docx", "pdf"]:
                raise ValueError(f"Unsupported export type: '{t}'. Must be 'docx' or 'pdf'.")
        return v


class BookExportFileItem(BaseSchema):
    """
    Represents metadata for a single generated file.
    """
    export_id: UUID | None = None
    export_type: str
    status: str
    file_name: str | None = None
    file_path: str | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    metadata: dict | None = None


class BookExportResponse(BaseSchema):
    """
    Aggregated response containing the assembly response and file export metadata.
    """
    book_id: UUID
    run_id: UUID | None = None
    status: str
    assembly: BookAssemblyResponse
    files: list[BookExportFileItem]
    metadata: dict | None = None


# ── Evaluation & Delivery Report Schemas ─────────────────────────────────────

class EvaluationReportRequest(BaseSchema):
    """
    Request model for triggering evaluation report generation.
    """
    book_id: UUID
    run_id: UUID | None = None
    include_chapter_checks: bool = True
    include_export_checks: bool = True
    include_trace_checks: bool = True
    include_memory_checks: bool = True
    persist_eval_results: bool = True
    metadata: dict | None = None


class EvaluationCheckItem(BaseSchema):
    """
    A single validation check item within the overall report.
    """
    check_name: str
    status: str
    score: float | None = None
    message: str
    details: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pass", "warning", "fail", "skipped"]
        if v not in valid:
            raise ValueError(f"status must be one of {valid}, got '{v}'")
        return v


class EvaluationReportResponse(BaseSchema):
    """
    Aggregated evaluation report.
    """
    book_id: UUID
    run_id: UUID | None = None
    status: str
    total_checks: int
    pass_count: int
    warning_count: int
    fail_count: int
    skipped_count: int
    checks: list[EvaluationCheckItem]
    markdown_report: str
    persisted_eval_ids: list[UUID] = Field(default_factory=list)
    metadata: dict | None = None


class PromptDossierRequest(BaseSchema):
    """
    Request model for prompt registry template inventory packaging.
    """
    include_templates: bool = True
    include_versions: bool = True
    include_agent_roles: bool = True
    include_render_examples: bool = True
    metadata: dict | None = None


class PromptDossierResponse(BaseSchema):
    """
    Complete prompts dossier report.
    """
    status: str
    agent_count: int
    template_count: int
    markdown_dossier: str
    prompts: list[dict]
    metadata: dict | None = None


class DeliveryBundleRequest(BaseSchema):
    """
    Request model for assembling and exporting delivery bundles.
    """
    book_id: UUID
    run_id: UUID | None = None
    include_eval_report: bool = True
    include_prompt_dossier: bool = True
    include_architecture_summary: bool = True
    include_memory_report: bool = True
    include_trace_summary: bool = True
    include_export_summary: bool = True
    write_files: bool = True
    metadata: dict | None = None


class DeliveryArtifactItem(BaseSchema):
    """
    Metadata for a single written delivery artifact file.
    """
    artifact_type: str
    status: str
    file_name: str | None = None
    file_path: str | None = None
    file_size_bytes: int | None = None
    error_message: str | None = None
    metadata: dict | None = None


class DeliveryBundleResponse(BaseSchema):
    """
    Aggregated response including manifest.json dictionary and artifacts metadata list.
    """
    book_id: UUID
    run_id: UUID | None = None
    status: str
    artifacts: list[DeliveryArtifactItem]
    manifest: dict
    metadata: dict | None = None


# ── Final QA & Assessment Readiness Schemas ───────────────────────────────────

class BackendReadinessCheckItem(BaseSchema):
    """
    Represent a single readiness check result.
    """
    check_name: str
    category: str
    status: str
    message: str
    details: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = ["pass", "warning", "fail", "skipped"]
        if v not in valid:
            raise ValueError(f"status must be one of {valid}, got '{v}'")
        return v


class BackendReadinessReportRequest(BaseSchema):
    """
    Request payload to configure readiness checks.
    """
    book_id: UUID | None = None
    run_id: UUID | None = None
    include_database_checks: bool = True
    include_api_checks: bool = True
    include_agent_checks: bool = True
    include_workflow_checks: bool = True
    include_export_checks: bool = True
    include_delivery_checks: bool = True
    include_safety_checks: bool = True
    metadata: dict | None = None


class BackendReadinessReportResponse(BaseSchema):
    """
    FastAPI envelope returning readiness report summaries and scorecard.
    """
    status: str
    total_checks: int
    pass_count: int
    warning_count: int
    fail_count: int
    skipped_count: int
    checks: list[BackendReadinessCheckItem]
    markdown_report: str
    metadata: dict | None = None


class EndToEndDryRunRequest(BaseSchema):
    """
    Request model for triggering synchronous, offline-safe sequential dry runs.
    """
    topic: str = Field(default="Modern RAG Systems for AI Engineers", min_length=1)
    genre: str = "technical guide"
    tone: str = "clear, practical, and mentor-like"
    create_sample_book: bool = True
    create_sample_chapters: bool = True
    run_mock_chapter_generation: bool = True
    run_memory_extraction: bool = True
    run_export_generation: bool = True
    run_delivery_bundle: bool = True
    max_chapters: int = Field(default=1, ge=1, le=3)
    metadata: dict | None = None


class EndToEndDryRunResponse(BaseSchema):
    """
    Response model detailing metrics for the dry run.
    """
    status: str
    book_id: UUID | None = None
    run_id: UUID | None = None
    chapter_ids: list[UUID] = Field(default_factory=list)
    generated_chapter_count: int = 0
    memory_written_count: int = 0
    export_file_count: int = 0
    delivery_artifact_count: int = 0
    checks: list[BackendReadinessCheckItem] = Field(default_factory=list)
    metadata: dict | None = None





