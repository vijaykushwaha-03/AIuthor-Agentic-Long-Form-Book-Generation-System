from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from app.schemas import (
    BookProjectCreate,
    BookProjectUpdate,
    BookProjectResponse,
    BookProjectListItem,
    BookRunCreate,
    BookRunStartRequest,
    BookRunUpdate,
    BookRunResponse,
    BookRunStatusResponse,
    TonePreset,
    BookStatus,
    RunStatus,
    AgentName,
)


def test_package_exports_book_run():
    """Verify all new schemas are properly exported from the package."""
    assert BookProjectCreate is not None
    assert BookProjectUpdate is not None
    assert BookProjectResponse is not None
    assert BookProjectListItem is not None
    assert BookRunCreate is not None
    assert BookRunStartRequest is not None
    assert BookRunUpdate is not None
    assert BookRunResponse is not None
    assert BookRunStatusResponse is not None


# ── BookProjectCreate Tests ──────────────────────────────────────────────────

def test_book_project_create_valid():
    """1. Valid data passes validation for BookProjectCreate."""
    data = {
        "topic": "Introduction to AI",
        "reader_profile": "Beginners in tech",
        "genre": "Educational",
        "tone": TonePreset.CONVERSATIONAL,
        "target_chapters": 10,
        "words_per_chapter": 2000,
        "project_metadata": {"difficulty": "easy"}
    }
    schema = BookProjectCreate(**data)
    assert schema.topic == "Introduction to AI"
    assert schema.target_chapters == 10
    assert schema.words_per_chapter == 2000


def test_book_project_create_empty_topic():
    """2. Empty topic fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="  ",
            reader_profile="Beginners",
            genre="Educational",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=5
        )


def test_book_project_create_too_short_topic():
    """3. Too-short topic (< 3 chars after stripping) fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="ab",
            reader_profile="Beginners",
            genre="Educational",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=5
        )


def test_book_project_create_invalid_tone():
    """4. Invalid tone preset fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="Introduction to AI",
            reader_profile="Beginners",
            genre="Educational",
            tone="angry_voice",  # Not a valid TonePreset
            target_chapters=5
        )


def test_book_project_create_target_chapters_below_1():
    """5. target_chapters below 1 fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="Introduction to AI",
            reader_profile="Beginners",
            genre="Educational",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=0
        )


def test_book_project_create_target_chapters_above_50():
    """6. target_chapters above 50 fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="Introduction to AI",
            reader_profile="Beginners",
            genre="Educational",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=51
        )


def test_book_project_create_words_per_chapter_below_300():
    """7. words_per_chapter below 300 fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="Introduction to AI",
            reader_profile="Beginners",
            genre="Educational",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=5,
            words_per_chapter=299
        )


def test_book_project_create_words_per_chapter_above_10000():
    """8. words_per_chapter above 10000 fails validation."""
    with pytest.raises(ValidationError):
        BookProjectCreate(
            topic="Introduction to AI",
            reader_profile="Beginners",
            genre="Educational",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=5,
            words_per_chapter=10001
        )


# ── BookProjectUpdate Tests ──────────────────────────────────────────────────

def test_book_project_update_partial_topic_only():
    """9. Partial update with only topic passes validation."""
    schema = BookProjectUpdate(topic="New Updated Topic")
    assert schema.topic == "New Updated Topic"
    assert schema.genre is None
    assert schema.status is None


def test_book_project_update_invalid_status():
    """10. Invalid status fails validation in BookProjectUpdate."""
    with pytest.raises(ValidationError):
        BookProjectUpdate(status="unknown_status")


# ── BookProjectResponse Tests ────────────────────────────────────────────────

def test_book_project_response_orm():
    """11. BookProjectResponse can validate from an ORM-like object (from_attributes)."""
    class MockProjectModel:
        def __init__(self):
            self.id = uuid4()
            self.topic = "FastAPI Development"
            self.reader_profile = "Intermediate Python devs"
            self.genre = "Programming"
            self.tone = TonePreset.CONVERSATIONAL
            self.target_chapters = 8
            self.words_per_chapter = 1500
            self.status = BookStatus.CREATED
            self.project_metadata = {"framework": "fastapi"}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockProjectModel()
    schema = BookProjectResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.topic == "FastAPI Development"
    assert schema.status == "created"
    assert schema.project_metadata == {"framework": "fastapi"}


# ── BookRunCreate Tests ──────────────────────────────────────────────────────

def test_book_run_create_valid():
    """12. Valid book_id and metadata passes validation for BookRunCreate."""
    book_id = uuid4()
    schema = BookRunCreate(book_id=book_id, run_metadata={"run_type": "full"})
    assert schema.book_id == book_id
    assert schema.run_metadata == {"run_type": "full"}


# ── BookRunUpdate Tests ──────────────────────────────────────────────────────

def test_book_run_update_valid():
    """13. Valid status and agent updates pass validation for BookRunUpdate."""
    schema = BookRunUpdate(status=RunStatus.RUNNING, current_agent=AgentName.PLANNER)
    assert schema.status == RunStatus.RUNNING
    assert schema.current_agent == AgentName.PLANNER


def test_book_run_update_long_error_message():
    """14. Error message exceeding 5000 characters fails validation."""
    long_msg = "x" * 5001
    with pytest.raises(ValidationError):
        BookRunUpdate(error_message=long_msg)


# ── BookRunStatusResponse Tests ──────────────────────────────────────────────

def test_book_run_status_response_progress_0():
    """15. progress_percentage of 0 passes validation."""
    schema = BookRunStatusResponse(
        run_id=uuid4(),
        book_id=uuid4(),
        status="running",
        current_agent="planner",
        progress_percentage=0.0
    )
    assert schema.progress_percentage == 0.0


def test_book_run_status_response_progress_100():
    """16. progress_percentage of 100 passes validation."""
    schema = BookRunStatusResponse(
        run_id=uuid4(),
        book_id=uuid4(),
        status="completed",
        current_agent=None,
        progress_percentage=100.0
    )
    assert schema.progress_percentage == 100.0


def test_book_run_status_response_progress_below_0():
    """17. progress_percentage below 0 fails validation."""
    with pytest.raises(ValidationError):
        BookRunStatusResponse(
            run_id=uuid4(),
            book_id=uuid4(),
            status="running",
            current_agent="planner",
            progress_percentage=-0.1
        )


def test_book_run_status_response_progress_above_100():
    """18. progress_percentage above 100 fails validation."""
    with pytest.raises(ValidationError):
        BookRunStatusResponse(
            run_id=uuid4(),
            book_id=uuid4(),
            status="running",
            current_agent="planner",
            progress_percentage=100.1
        )
