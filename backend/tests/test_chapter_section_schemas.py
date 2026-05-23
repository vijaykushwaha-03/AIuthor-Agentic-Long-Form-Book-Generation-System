from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from app.schemas import (
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
    ChapterStatus,
    SectionStatus,
    TonePreset,
)


def test_package_exports_chapter_section():
    """21. Verify all new schemas are properly exported from the package."""
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


# ── ChapterContract Tests ────────────────────────────────────────────────────

def test_chapter_contract_valid():
    """1. Valid contract passes validation."""
    data = {
        "chapter_number": 1,
        "title": "Introduction to Algorithms",
        "purpose": "Define algorithms and trace historical context.",
        "key_concepts": ["complexity", "correctness"],
        "required_facts": ["sorting runs in O(N log N)"],
        "callback_opportunities": ["refer to binary search later"],
        "estimated_word_count": 1500,
        "metadata": {"editor": "Alice"}
    }
    schema = ChapterContract(**data)
    assert schema.chapter_number == 1
    assert schema.estimated_word_count == 1500


def test_chapter_contract_chapter_number_below_1():
    """2. chapter_number below 1 fails validation."""
    with pytest.raises(ValidationError):
        ChapterContract(
            chapter_number=0,
            title="Introduction",
            purpose="Define algorithms"
        )


def test_chapter_contract_title_too_short():
    """3. title too short (< 2 chars after stripping) fails validation."""
    with pytest.raises(ValidationError):
        ChapterContract(
            chapter_number=1,
            title=" a ",  # Stripped to "a", length 1
            purpose="Define algorithms"
        )


def test_chapter_contract_estimated_word_count_below_100():
    """4. estimated_word_count below 100 fails validation."""
    with pytest.raises(ValidationError):
        ChapterContract(
            chapter_number=1,
            title="Introduction",
            purpose="Define algorithms",
            estimated_word_count=99
        )


# ── ChapterCreate Tests ──────────────────────────────────────────────────────

def test_chapter_create_valid():
    """5. Valid data passes validation for ChapterCreate."""
    book_id = uuid4()
    schema = ChapterCreate(
        book_id=book_id,
        chapter_number=2,
        title="Sorting",
        summary="A chapter about sorting",
        tone=TonePreset.ACADEMIC,
        status=ChapterStatus.PLANNED
    )
    assert schema.book_id == book_id
    assert schema.status == ChapterStatus.PLANNED


def test_chapter_create_invalid_chapter_number():
    """6. Invalid chapter_number (> 100) fails validation."""
    with pytest.raises(ValidationError):
        ChapterCreate(
            book_id=uuid4(),
            chapter_number=101,
            title="Out of Bounds",
            status=ChapterStatus.PLANNED
        )


def test_chapter_create_invalid_status():
    """7. Invalid status fails validation."""
    with pytest.raises(ValidationError):
        ChapterCreate(
            book_id=uuid4(),
            chapter_number=5,
            title="Sort",
            status="invalid_status"
        )


# ── ChapterUpdate Tests ──────────────────────────────────────────────────────

def test_chapter_update_partial_valid():
    """8. Partial update with final_text passes validation."""
    schema = ChapterUpdate(final_text="This is the final text of the chapter.")
    assert schema.final_text == "This is the final text of the chapter."
    assert schema.title is None
    assert schema.word_count is None


def test_chapter_update_word_count_below_0():
    """9. word_count below 0 fails validation."""
    with pytest.raises(ValidationError):
        ChapterUpdate(word_count=-1)


# ── ChapterInsertRequest Tests ───────────────────────────────────────────────

def test_chapter_insert_request_after_chapter_0():
    """10. after_chapter 0 passes validation (insert before chapter 1)."""
    schema = ChapterInsertRequest(
        after_chapter=0,
        title="Chapter Zero",
        purpose="Setup basic terminology"
    )
    assert schema.after_chapter == 0


def test_chapter_insert_request_after_chapter_below_0():
    """11. after_chapter below 0 fails validation."""
    with pytest.raises(ValidationError):
        ChapterInsertRequest(
            after_chapter=-1,
            title="Negative Chapter",
            purpose="Setup basic terminology"
        )


def test_chapter_insert_request_invalid_title():
    """12. Invalid (too short) title fails validation."""
    with pytest.raises(ValidationError):
        ChapterInsertRequest(
            after_chapter=1,
            title="x",
            purpose="Setup basic terminology"
        )


# ── ChapterResponse Tests ────────────────────────────────────────────────────

def test_chapter_response_orm():
    """13. ChapterResponse can validate from an ORM-like object."""
    class MockChapter:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.chapter_number = 3
            self.title = "Trees and Graphs"
            self.summary = "A chapter about hierarchical structures"
            self.chapter_contract = {"concepts": ["DFS", "BFS"]}
            self.draft_text = "Draft content"
            self.humanized_text = "Humanized content"
            self.edited_text = "Edited content"
            self.final_text = "Final content"
            self.tone = "academic"
            self.status = "completed"
            self.word_count = 1200
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockChapter()
    schema = ChapterResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.title == "Trees and Graphs"
    assert schema.status == "completed"
    assert schema.word_count == 1200


# ── BookSectionCreate Tests ──────────────────────────────────────────────────

def test_book_section_create_valid():
    """14. Valid front matter section passes validation."""
    book_id = uuid4()
    schema = BookSectionCreate(
        book_id=book_id,
        section_type="copyright",
        title="Copyright Page",
        content="All rights reserved.",
        sort_order=3,
        status=SectionStatus.DRAFT
    )
    assert schema.book_id == book_id
    assert schema.section_type == "copyright"
    assert schema.status == SectionStatus.DRAFT


def test_book_section_create_sort_order_below_0():
    """15. sort_order below 0 fails validation."""
    with pytest.raises(ValidationError):
        BookSectionCreate(
            book_id=uuid4(),
            section_type="toc",
            sort_order=-1
        )


def test_book_section_create_invalid_status():
    """16. Invalid status fails validation."""
    with pytest.raises(ValidationError):
        BookSectionCreate(
            book_id=uuid4(),
            section_type="toc",
            sort_order=1,
            status="archived"
        )


# ── BookSectionUpdate Tests ──────────────────────────────────────────────────

def test_book_section_update_partial():
    """17. Partial content update passes validation."""
    schema = BookSectionUpdate(content="New updated content for epigraph.")
    assert schema.content == "New updated content for epigraph."
    assert schema.title is None
    assert schema.sort_order is None


# ── BookSectionResponse Tests ────────────────────────────────────────────────

def test_book_section_response_orm():
    """18. BookSectionResponse can validate from an ORM-like object."""
    class MockBookSection:
        def __init__(self):
            self.id = uuid4()
            self.book_id = uuid4()
            self.section_type = "dedication"
            self.title = "Dedications"
            self.content = "Dedicated to the readers."
            self.sort_order = 4
            self.status = "completed"
            self.section_metadata = {"pages": 1}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockBookSection()
    schema = BookSectionResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.section_type == "dedication"
    assert schema.status == "completed"
    assert schema.section_metadata == {"pages": 1}


# ── Constants Tests ──────────────────────────────────────────────────────────

def test_constants_front_matter_contains_toc():
    """19. REQUIRED_FRONT_MATTER_SECTIONS contains 'toc'."""
    assert "toc" in REQUIRED_FRONT_MATTER_SECTIONS


def test_constants_back_matter_contains_glossary():
    """20. REQUIRED_BACK_MATTER_SECTIONS contains 'glossary'."""
    assert "glossary" in REQUIRED_BACK_MATTER_SECTIONS
