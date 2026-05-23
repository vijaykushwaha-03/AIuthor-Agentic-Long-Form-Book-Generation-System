from __future__ import annotations

import pytest
from uuid import uuid4
from app.schemas import (
    BaseSchema,
    IDSchema,
    TimestampSchema,
    ORMBaseSchema,
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
    PaginationParams,
    PaginatedResponse,
    SortParams,
    MessageResponse,
    HealthResponse,
    VersionResponse,
    ErrorResponse,
    ValidationErrorResponse,
    InternalErrorResponse,
    BookProjectCreate,
    BookProjectUpdate,
    BookProjectResponse,
    BookProjectListItem,
    BookRunCreate,
    BookRunStartRequest,
    BookRunUpdate,
    BookRunResponse,
    BookRunStatusResponse,
    ChapterContract,
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterListItem,
    ChapterInsertRequest,
    BookSectionCreate,
    BookSectionUpdate,
    BookSectionResponse,
    BookSectionListItem,
    REQUIRED_FRONT_MATTER_SECTIONS,
    REQUIRED_BACK_MATTER_SECTIONS,
)


def test_core_schemas_importable():
    """1. Verify all core schemas can be imported from app.schemas."""
    assert BaseSchema is not None
    assert IDSchema is not None
    assert TimestampSchema is not None
    assert ORMBaseSchema is not None
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
    assert PaginationParams is not None
    assert PaginatedResponse is not None
    assert SortParams is not None
    assert MessageResponse is not None
    assert HealthResponse is not None
    assert VersionResponse is not None
    assert ErrorResponse is not None
    assert ValidationErrorResponse is not None
    assert InternalErrorResponse is not None
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


def test_book_project_create_payload_validates():
    """2. BookProjectCreate sample payload validates correctly."""
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
    assert schema.topic == "Personal Finance for Beginners"
    assert schema.words_per_chapter == 2500
    assert schema.tone == TonePreset.CONVERSATIONAL


def test_book_run_start_request_payload_validates():
    """3. BookRunStartRequest sample payload validates correctly."""
    payload = {
        "run_metadata": {
            "run_mode": "dry_run",
            "debug": True
        }
    }
    schema = BookRunStartRequest(**payload)
    assert schema.run_metadata == {"run_mode": "dry_run", "debug": True}


def test_chapter_contract_payload_validates():
    """4. ChapterContract sample payload validates correctly."""
    payload = {
        "chapter_number": 1,
        "title": "Understanding Your Income",
        "purpose": "Explain the difference between gross and net income.",
        "key_concepts": [
            "gross income",
            "net income",
            "withholding taxes"
        ],
        "required_facts": [
            "Net income is income after taxes and deductions."
        ],
        "callback_opportunities": [
            "Reference net income when discussing budgeting in Chapter 2."
        ],
        "estimated_word_count": 1500,
        "metadata": {
            "difficulty_rating": "beginner"
        }
    }
    schema = ChapterContract(**payload)
    assert schema.chapter_number == 1
    assert schema.estimated_word_count == 1500
    assert "gross income" in schema.key_concepts


def test_chapter_insert_request_test_d_payload_validates():
    """5. ChapterInsertRequest Test D sample validates correctly."""
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


def test_book_section_create_toc_payload_validates():
    """6. BookSectionCreate TOC sample validates correctly."""
    payload = {
        "book_id": uuid4(),
        "section_type": "toc",
        "title": "Table of Contents",
        "content": "1. Understanding Your Income\n2. Creating Your First Budget",
        "sort_order": 5,
        "status": "generated",
        "section_metadata": {
            "auto_generated": True
        }
    }
    schema = BookSectionCreate(**payload)
    assert schema.section_type == "toc"
    assert schema.sort_order == 5
    assert schema.status == SectionStatus.GENERATED


def test_book_section_update_glossary_payload_validates():
    """7. BookSectionUpdate glossary sample validates correctly."""
    payload = {
        "content": "Gross Income: Total pay before taxes.\nNet Income: Take-home pay after deductions.",
        "status": "completed"
    }
    schema = BookSectionUpdate(**payload)
    assert schema.status == SectionStatus.COMPLETED
    assert "Gross Income" in schema.content


def test_required_front_matter_sections_values():
    """8. REQUIRED_FRONT_MATTER_SECTIONS contains all 10 required values."""
    expected = [
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
    for val in expected:
        assert val in REQUIRED_FRONT_MATTER_SECTIONS


def test_required_back_matter_sections_values():
    """9. REQUIRED_BACK_MATTER_SECTIONS contains all 6 required values."""
    expected = [
        "afterword",
        "appendix",
        "glossary",
        "references",
        "about_author",
        "back_cover_copy",
    ]
    for val in expected:
        assert val in REQUIRED_BACK_MATTER_SECTIONS
