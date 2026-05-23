from __future__ import annotations

import importlib
import pytest
from pydantic import ValidationError
from uuid import uuid4

# Import package-level schemas and constants
from app.schemas import (
    # Base
    BaseSchema,
    IDSchema,
    TimestampSchema,
    ORMBaseSchema,
    # Common
    PaginationParams,
    PaginatedResponse,
    SortParams,
    MessageResponse,
    HealthResponse,
    VersionResponse,
    # Errors
    ErrorResponse,
    ValidationErrorResponse,
    InternalErrorResponse,
    # Enums
    TonePreset,
    BookStatus,
    RunStatus,
    ChapterStatus,
    SectionStatus,
    AgentName,
    AgentStatus,
    MemoryOperation,
    EvalStatus,
    ExportType,
    ExportStatus,
    # Book
    BookProjectCreate,
    BookProjectUpdate,
    BookProjectResponse,
    BookProjectListItem,
    # Run
    BookRunCreate,
    BookRunStartRequest,
    BookRunUpdate,
    BookRunResponse,
    BookRunStatusResponse,
    # Chapter
    ChapterContract,
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterListItem,
    ChapterInsertRequest,
    # Section
    BookSectionCreate,
    BookSectionUpdate,
    BookSectionResponse,
    BookSectionListItem,
    REQUIRED_FRONT_MATTER_SECTIONS,
    REQUIRED_BACK_MATTER_SECTIONS,
    # RAG
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
    # Memory
    FactRegistryCreate,
    FactRegistryUpdate,
    FactRegistryResponse,
    ConceptBibleCreate,
    ConceptBibleUpdate,
    ConceptBibleResponse,
    CharacterBibleCreate,
    CharacterBibleUpdate,
    CharacterBibleResponse,
    CallbackIndexCreate,
    CallbackIndexUpdate,
    CallbackIndexResponse,
    ToneFingerprintCreate,
    ToneFingerprintUpdate,
    ToneFingerprintResponse,
    DecisionLogCreate,
    DecisionLogUpdate,
    DecisionLogResponse,
    MemoryReadRequest,
    MemoryReadResponse,
    MemoryWriteRequest,
    MemoryWriteResponse,
    # Observability
    AgentTraceCreate,
    AgentTraceUpdate,
    AgentTraceResponse,
    PromptLogCreate,
    PromptLogUpdate,
    PromptLogResponse,
    MemoryIOLogCreate,
    MemoryIOLogResponse,
    TokenCostLedgerCreate,
    TokenCostLedgerUpdate,
    TokenCostLedgerResponse,
    TraceBundleResponse,
    RunCostSummaryResponse,
    # Eval
    EvalResultCreate,
    EvalResultUpdate,
    EvalResultResponse,
    EvalMetricSummary,
    EvalReportResponse,
    # Export
    ExportFileCreate,
    ExportFileUpdate,
    ExportFileResponse,
    ExportFileListItem,
    ExportBundleResponse,
    ExportRequest,
    ExportResponse,
)


# ── 1. Importability Check ───────────────────────────────────────────────────

def test_all_schema_modules_importable():
    """Verify that all Pydantic schema modules are fully importable."""
    modules = [
        "app.schemas.base",
        "app.schemas.enums",
        "app.schemas.common",
        "app.schemas.errors",
        "app.schemas.book",
        "app.schemas.run",
        "app.schemas.chapter",
        "app.schemas.section",
        "app.schemas.rag",
        "app.schemas.memory",
        "app.schemas.observability",
        "app.schemas.eval",
        "app.schemas.export",
    ]
    for module_name in modules:
        mod = importlib.import_module(module_name)
        assert mod is not None


# ── 2. Exports Check ──────────────────────────────────────────────────────────

def test_all_expected_schemas_exported_from_package():
    """Verify that all schema classes and constants are exported from the main schemas package."""
    assert BaseSchema is not None
    assert IDSchema is not None
    assert TimestampSchema is not None
    assert ORMBaseSchema is not None
    assert PaginationParams is not None
    assert PaginatedResponse is not None
    assert SortParams is not None
    assert MessageResponse is not None
    assert HealthResponse is not None
    assert VersionResponse is not None
    assert ErrorResponse is not None
    assert ValidationErrorResponse is not None
    assert InternalErrorResponse is not None
    assert TonePreset is not None
    assert BookStatus is not None
    assert RunStatus is not None
    assert ChapterStatus is not None
    assert SectionStatus is not None
    assert AgentName is not None
    assert AgentStatus is not None
    assert MemoryOperation is not None
    assert EvalStatus is not None
    assert ExportType is not None
    assert ExportStatus is not None
    assert BookProjectCreate is not None
    assert BookProjectUpdate is not None
    assert BookProjectResponse is not None
    assert BookProjectListItem is not None
    assert BookRunCreate is not None
    assert BookRunStartRequest is not None
    assert BookRunUpdate is not None
    assert BookRunResponse is not None
    assert BookRunStatusResponse is not None
    assert ChapterContract is not None
    assert ChapterCreate is not None
    assert ChapterUpdate is not None
    assert ChapterResponse is not None
    assert ChapterListItem is not None
    assert ChapterInsertRequest is not None
    assert BookSectionCreate is not None
    assert BookSectionUpdate is not None
    assert BookSectionResponse is not None
    assert BookSectionListItem is not None
    assert REQUIRED_FRONT_MATTER_SECTIONS is not None
    assert REQUIRED_BACK_MATTER_SECTIONS is not None
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
    assert FactRegistryCreate is not None
    assert FactRegistryUpdate is not None
    assert FactRegistryResponse is not None
    assert ConceptBibleCreate is not None
    assert ConceptBibleUpdate is not None
    assert ConceptBibleResponse is not None
    assert CharacterBibleCreate is not None
    assert CharacterBibleUpdate is not None
    assert CharacterBibleResponse is not None
    assert CallbackIndexCreate is not None
    assert CallbackIndexUpdate is not None
    assert CallbackIndexResponse is not None
    assert ToneFingerprintCreate is not None
    assert ToneFingerprintUpdate is not None
    assert ToneFingerprintResponse is not None
    assert DecisionLogCreate is not None
    assert DecisionLogUpdate is not None
    assert DecisionLogResponse is not None
    assert MemoryReadRequest is not None
    assert MemoryReadResponse is not None
    assert MemoryWriteRequest is not None
    assert MemoryWriteResponse is not None
    assert AgentTraceCreate is not None
    assert AgentTraceUpdate is not None
    assert AgentTraceResponse is not None
    assert PromptLogCreate is not None
    assert PromptLogUpdate is not None
    assert PromptLogResponse is not None
    assert MemoryIOLogCreate is not None
    assert MemoryIOLogResponse is not None
    assert TokenCostLedgerCreate is not None
    assert TokenCostLedgerUpdate is not None
    assert TokenCostLedgerResponse is not None
    assert TraceBundleResponse is not None
    assert RunCostSummaryResponse is not None
    assert EvalResultCreate is not None
    assert EvalResultUpdate is not None
    assert EvalResultResponse is not None
    assert EvalMetricSummary is not None
    assert EvalReportResponse is not None
    assert ExportFileCreate is not None
    assert ExportFileUpdate is not None
    assert ExportFileResponse is not None
    assert ExportFileListItem is not None
    assert ExportBundleResponse is not None
    assert ExportRequest is not None
    assert ExportResponse is not None


# ── 3. Front/Back Matter Constants Duplication Check ──────────────────────────

def test_no_duplicate_required_section_values():
    """Verify that REQUIRED_FRONT_MATTER_SECTIONS and REQUIRED_BACK_MATTER_SECTIONS have no duplicate items."""
    assert len(REQUIRED_FRONT_MATTER_SECTIONS) == len(set(REQUIRED_FRONT_MATTER_SECTIONS))
    assert len(REQUIRED_BACK_MATTER_SECTIONS) == len(set(REQUIRED_BACK_MATTER_SECTIONS))


# ── 4. Required Book Sections Completeness Check ──────────────────────────────

def test_required_book_structure_sections_complete():
    """Verify all expected front and back matter structure components are present."""
    expected_front = [
        "half_title",
        "title_page",
        "copyright",
        "dedication",
        "epigraph",
        "toc",
        "foreword",
        "preface",
        "acknowledgments",
        "introduction",
    ]
    for section in expected_front:
        assert section in REQUIRED_FRONT_MATTER_SECTIONS

    expected_back = [
        "afterword",
        "appendix",
        "glossary",
        "references",
        "about_author",
        "back_cover_copy",
    ]
    for section in expected_back:
        assert section in REQUIRED_BACK_MATTER_SECTIONS


# ── 5. Test A Payload Verification ────────────────────────────────────────────

def test_test_a_payload_contract_validates():
    """Validate sample BookProjectCreate payload contract for Test Case A."""
    payload = {
        "topic": "Personal Finance for Beginners",
        "reader_profile": "Adults with no prior finance background",
        "genre": "non-fiction guide",
        "tone": "conversational",
        "target_chapters": 10,
        "words_per_chapter": 2500,
        "project_metadata": {
            "test_case": "A"
        }
    }
    schema = BookProjectCreate(**payload)
    assert schema.topic == payload["topic"]
    assert schema.tone == TonePreset.CONVERSATIONAL
    assert schema.project_metadata == {"test_case": "A"}


# ── 6. Test B Payload Verification ────────────────────────────────────────────

def test_test_b_payload_contract_validates():
    """Validate sample BookProjectCreate novella payload contract for Test Case B."""
    payload = {
        "topic": "A quiet story about two friends rebuilding trust",
        "reader_profile": "Adult fiction readers",
        "genre": "novella",
        "tone": "storyteller",
        "target_chapters": 5,
        "words_per_chapter": 1800,
        "project_metadata": {
            "test_case": "B",
            "characters": ["Maya", "Arjun"]
        }
    }
    schema = BookProjectCreate(**payload)
    assert schema.topic == payload["topic"]
    assert schema.tone == TonePreset.STORYTELLER
    assert schema.project_metadata["characters"] == ["Maya", "Arjun"]


# ── 7. Test C Tone Variants Validation ────────────────────────────────────────

def test_test_c_tone_variants_validate():
    """Validate academic, motivational, and witty tone settings against BookProjectUpdate."""
    for tone in ["academic", "motivational", "witty"]:
        schema = BookProjectUpdate(tone=tone)
        assert schema.tone == tone

    # Invalid tone must fail
    with pytest.raises(ValidationError):
        BookProjectUpdate(tone="romantic")


# ── 8. Test D Insert Payload Verification ──────────────────────────────────────

def test_test_d_insert_payload_validates():
    """Validate ChapterInsertRequest payload contract for Test Case D."""
    payload = {
        "after_chapter": 4,
        "title": "Understanding Credit Without Fear",
        "purpose": "Bridge budgeting and long-term planning",
        "tone": "conversational",
        "metadata": {
            "repair_required": True
        }
    }
    schema = ChapterInsertRequest(**payload)
    assert schema.after_chapter == 4
    assert schema.title == "Understanding Credit Without Fear"
    assert schema.metadata == {"repair_required": True}


# ── 9. Trace Bundle Schema Verification ───────────────────────────────────────

def test_trace_bundle_schema_validates_empty():
    """Verify TraceBundleResponse validates with empty defaults."""
    run_id = uuid4()
    schema = TraceBundleResponse(
        run_id=run_id,
        status="success",
        total_prompt_logs=0,
        total_trace_records=0
    )
    assert schema.run_id == run_id
    assert schema.status == "success"
    assert schema.traces == []
    assert schema.total_trace_records == 0


# ── 10. Eval Report Schema Verification ───────────────────────────────────────

def test_eval_report_schema_validates_empty():
    """Verify EvalReportResponse validates with empty metrics and zero counts."""
    book_id = uuid4()
    schema = EvalReportResponse(
        book_id=book_id,
        overall_status="pending",
        total_evals=0,
        passed_evals=0
    )
    assert schema.book_id == book_id
    assert schema.overall_status == "pending"
    assert schema.metrics == []
    assert schema.total_evals == 0


# ── 11. Export Request Schema Verification ────────────────────────────────────

def test_export_request_schema_validates_docx_pdf():
    """Verify ExportRequest validates with docx and pdf exports."""
    book_id = uuid4()
    schema = ExportRequest(
        book_id=book_id,
        export_types=["docx", "pdf"]
    )
    assert schema.book_id == book_id
    assert schema.export_types == ["docx", "pdf"]


# ── 12. Memory Write Schema Verification ──────────────────────────────────────

def test_memory_write_schema_validates_empty_groups():
    """Verify MemoryWriteRequest validates with empty facts, concepts, etc."""
    book_id = uuid4()
    schema = MemoryWriteRequest(
        book_id=book_id,
        operation=MemoryOperation.WRITE
    )
    assert schema.book_id == book_id
    assert schema.operation == MemoryOperation.WRITE
    assert schema.facts == []
    assert schema.concepts == []
    assert schema.tone_fingerprints == []


# ── 13. DB Dependency-Free Verification ───────────────────────────────────────

def test_schema_layer_has_no_db_dependency():
    """Ensure schemas can be imported, instantiated, and validated without any database connection."""
    # Instantiating schema relies strictly on local validation rules, requiring no active connection
    schema = VersionResponse(service="AIuthor Backend", version="1.0.0")
    assert schema.service == "AIuthor Backend"
    assert schema.version == "1.0.0"
