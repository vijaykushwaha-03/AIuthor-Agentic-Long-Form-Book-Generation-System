from __future__ import annotations

import sys
from enum import Enum

# Check for StrEnum availability (Python 3.11+)
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    class StrEnum(str, Enum):
        """Fallback StrEnum for Python < 3.11 compatibility."""
        pass


class TonePreset(StrEnum):
    CONVERSATIONAL = "conversational"
    ACADEMIC = "academic"
    STORYTELLER = "storyteller"
    MOTIVATIONAL = "motivational"
    WITTY = "witty"


class BookStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChapterStatus(StrEnum):
    PLANNED = "planned"
    DRAFTING = "drafting"
    HUMANIZING = "humanizing"
    EDITING = "editing"
    FACT_CHECKING = "fact_checking"
    COMPLETED = "completed"
    FAILED = "failed"


class SectionStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentName(StrEnum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    WRITER = "writer"
    HUMANIZER = "humanizer"
    EDITOR = "editor"
    FACT_CHECKER = "fact_checker"
    MEMORY_KEEPER = "memory_keeper"
    ASSEMBLER = "assembler"
    EVALS = "evals"


class AgentStatus(StrEnum):
    PENDING = "pending"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_REPAIR = "needs_repair"


class MemoryOperation(StrEnum):
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"


class EvalStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ExportType(StrEnum):
    DOCX = "docx"
    PDF = "pdf"
    PROMPT_DOSSIER = "prompt_dossier"
    TRACE_BUNDLE = "trace_bundle"
    EVAL_REPORT = "eval_report"
    SAMPLE_BOOKS_ZIP = "sample_books_zip"


class ExportStatus(StrEnum):
    CREATED = "created"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"
