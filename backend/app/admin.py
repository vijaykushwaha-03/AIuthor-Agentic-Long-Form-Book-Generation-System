from __future__ import annotations

from fastapi import FastAPI
from sqladmin import Admin, ModelView

from app.database import get_engine
from app.models import (
    BookProject,
    BookSection,
    Chapter,
    BookRun,
    SourceDocument,
    DocumentChunk,
    FactRegistry,
    ConceptBible,
    CharacterBible,
    CallbackIndex,
    ToneFingerprint,
    DecisionLog,
    AgentTrace,
    PromptLog,
    MemoryIOLog,
    TokenCostLedger,
    EvalResult,
    ExportFile,
)


class BookProjectAdmin(ModelView, model=BookProject):
    column_list = ["id", "genre", "tone", "status", "target_chapters", "created_at"]
    column_searchable_list = ["genre", "tone", "status", "topic"]
    name = "Book Project"
    name_plural = "Book Projects"
    icon = "fa-solid fa-book"


class BookSectionAdmin(ModelView, model=BookSection):
    column_list = ["id", "book_id", "section_type", "title", "sort_order", "status"]
    column_searchable_list = ["section_type", "title", "status"]
    name = "Book Section"
    name_plural = "Book Sections"
    icon = "fa-solid fa-section"


class ChapterAdmin(ModelView, model=Chapter):
    column_list = ["id", "book_id", "chapter_number", "title", "status", "word_count"]
    column_searchable_list = ["title", "summary", "status"]
    name = "Chapter"
    name_plural = "Chapters"
    icon = "fa-solid fa-file-lines"


class BookRunAdmin(ModelView, model=BookRun):
    column_list = ["id", "book_id", "status", "current_agent", "started_at", "completed_at"]
    column_searchable_list = ["status", "current_agent"]
    name = "Book Run"
    name_plural = "Book Runs"
    icon = "fa-solid fa-play"


class SourceDocumentAdmin(ModelView, model=SourceDocument):
    column_list = ["id", "book_id", "title", "source_type", "status"]
    column_searchable_list = ["title", "source_type", "status"]
    name = "Source Document"
    name_plural = "Source Documents"
    icon = "fa-solid fa-file-pdf"


class DocumentChunkAdmin(ModelView, model=DocumentChunk):
    column_list = ["id", "document_id", "book_id", "chunk_index", "token_count", "embedding_status"]
    column_details_exclude_list = ["embedding"]
    form_excluded_columns = ["embedding"]
    column_searchable_list = ["chunk_text", "embedding_status"]
    name = "Document Chunk"
    name_plural = "Document Chunks"
    icon = "fa-solid fa-puzzle-piece"


class FactRegistryAdmin(ModelView, model=FactRegistry):
    column_list = ["id", "book_id", "claim", "confidence", "status"]
    column_searchable_list = ["claim", "status"]
    name = "Fact Registry"
    name_plural = "Fact Registry Entries"
    icon = "fa-solid fa-check-double"


class ConceptBibleAdmin(ModelView, model=ConceptBible):
    column_list = ["id", "book_id", "concept", "first_chapter"]
    column_searchable_list = ["concept", "definition"]
    name = "Concept Bible"
    name_plural = "Concept Bible Entries"
    icon = "fa-solid fa-brain"


class CharacterBibleAdmin(ModelView, model=CharacterBible):
    column_list = ["id", "book_id", "character_name", "role"]
    column_searchable_list = ["character_name", "role", "arc_summary"]
    name = "Character Bible"
    name_plural = "Character Bible Entries"
    icon = "fa-solid fa-user-gear"


class CallbackIndexAdmin(ModelView, model=CallbackIndex):
    column_list = ["id", "book_id", "source_chapter", "target_chapter", "concept", "status"]
    column_searchable_list = ["concept", "callback_text", "status"]
    name = "Callback Index"
    name_plural = "Callback Index Entries"
    icon = "fa-solid fa-reply"


class ToneFingerprintAdmin(ModelView, model=ToneFingerprint):
    column_list = ["id", "book_id", "tone_name"]
    column_searchable_list = ["tone_name"]
    name = "Tone Fingerprint"
    name_plural = "Tone Fingerprints"
    icon = "fa-solid fa-fingerprint"


class DecisionLogAdmin(ModelView, model=DecisionLog):
    column_list = ["id", "book_id", "decision"]
    column_searchable_list = ["decision", "reason", "impact"]
    name = "Decision Log"
    name_plural = "Decision Logs"
    icon = "fa-solid fa-gavel"


class AgentTraceAdmin(ModelView, model=AgentTrace):
    column_list = ["id", "run_id", "book_id", "agent_name", "status", "started_at", "completed_at"]
    column_searchable_list = ["agent_name", "status"]
    name = "Agent Trace"
    name_plural = "Agent Traces"
    icon = "fa-solid fa-chart-line"


class PromptLogAdmin(ModelView, model=PromptLog):
    column_list = ["id", "run_id", "book_id", "agent_name", "model_name", "prompt_name"]
    column_searchable_list = ["agent_name", "model_name", "prompt_name"]
    name = "Prompt Log"
    name_plural = "Prompt Logs"
    icon = "fa-solid fa-terminal"


class MemoryIOLogAdmin(ModelView, model=MemoryIOLog):
    column_list = ["id", "run_id", "book_id", "agent_name", "operation", "memory_type"]
    column_searchable_list = ["agent_name", "operation", "memory_type"]
    name = "Memory IO Log"
    name_plural = "Memory IO Logs"
    icon = "fa-solid fa-database"


class TokenCostLedgerAdmin(ModelView, model=TokenCostLedger):
    column_list = ["id", "run_id", "book_id", "agent_name", "model_name", "total_tokens", "estimated_cost"]
    column_searchable_list = ["agent_name", "model_name"]
    name = "Token Cost Ledger"
    name_plural = "Token Cost Ledgers"
    icon = "fa-solid fa-coins"


class EvalResultAdmin(ModelView, model=EvalResult):
    column_list = ["id", "run_id", "book_id", "eval_name", "score", "status"]
    column_searchable_list = ["eval_name", "status"]
    name = "Evaluation Result"
    name_plural = "Evaluation Results"
    icon = "fa-solid fa-square-poll-vertical"


class ExportFileAdmin(ModelView, model=ExportFile):
    column_list = ["id", "book_id", "run_id", "export_type", "file_name", "status"]
    column_searchable_list = ["export_type", "file_name", "status"]
    name = "Export File"
    name_plural = "Export Files"
    icon = "fa-solid fa-file-export"


def setup_admin(app: FastAPI) -> Admin:
    """Setup SQLAdmin interface with all 18 database model views."""
    engine = get_engine()
    admin = Admin(app, engine)

    # Register views
    admin.add_view(BookProjectAdmin)
    admin.add_view(BookSectionAdmin)
    admin.add_view(ChapterAdmin)
    admin.add_view(BookRunAdmin)
    admin.add_view(SourceDocumentAdmin)
    admin.add_view(DocumentChunkAdmin)
    admin.add_view(FactRegistryAdmin)
    admin.add_view(ConceptBibleAdmin)
    admin.add_view(CharacterBibleAdmin)
    admin.add_view(CallbackIndexAdmin)
    admin.add_view(ToneFingerprintAdmin)
    admin.add_view(DecisionLogAdmin)
    admin.add_view(AgentTraceAdmin)
    admin.add_view(PromptLogAdmin)
    admin.add_view(MemoryIOLogAdmin)
    admin.add_view(TokenCostLedgerAdmin)
    admin.add_view(EvalResultAdmin)
    admin.add_view(ExportFileAdmin)

    return admin
