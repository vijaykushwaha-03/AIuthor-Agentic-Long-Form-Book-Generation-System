from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.book import BookProject, BookSection
from app.models.run import BookRun
from app.models.chapter import Chapter


def test_base_metadata_contains_tables():
    """Verify that all core book tables are registered in SQLAlchemy metadata."""
    expected_tables = {"book_projects", "book_runs", "chapters", "book_sections"}
    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_core_book_models_lifecycle():
    """Verify instantiation, relationships, cascades, and constraints on SQLite."""
    # Setup in-memory SQLite database for isolated unit test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. Instantiate BookProject
        project = BookProject(
            topic="Beginner Personal Finance Guide",
            reader_profile="Young adults aged 18-25 seeking basic budget tips",
            genre="Finance",
            tone="Conversational",
            target_chapters=10,
            words_per_chapter=2000,
            status="created",
            project_metadata={"tags": ["money", "savings"]},
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        assert isinstance(project.id, uuid.UUID)
        assert project.topic == "Beginner Personal Finance Guide"
        assert project.status == "created"
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

        # 2. Instantiate BookRun
        run = BookRun(
            book_id=project.id,
            status="pending",
            current_agent="PlannerAgent",
            run_metadata={"workflow_version": "1.0"},
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        assert isinstance(run.id, uuid.UUID)
        assert run.book_id == project.id
        assert run.status == "pending"
        assert run.current_agent == "PlannerAgent"
        assert run.book == project
        assert run in project.runs

        # 3. Instantiate Chapter
        chapter1 = Chapter(
            book_id=project.id,
            chapter_number=1,
            title="Introduction to Saving",
            summary="A brief intro to the importance of savings.",
            chapter_contract={"must_contain": ["budget", "compounding"]},
            status="planned",
            word_count=1500,
        )
        session.add(chapter1)
        session.commit()
        session.refresh(chapter1)

        assert isinstance(chapter1.id, uuid.UUID)
        assert chapter1.book_id == project.id
        assert chapter1.chapter_number == 1
        assert chapter1.title == "Introduction to Saving"
        assert chapter1.status == "planned"
        assert chapter1.book == project
        assert chapter1 in project.chapters

        # 4. Instantiate BookSection
        section = BookSection(
            book_id=project.id,
            section_type="dedication",
            title="Dedication Page",
            content="Dedicated to those who start small.",
            sort_order=1,
            status="draft",
        )
        session.add(section)
        session.commit()
        session.refresh(section)

        assert isinstance(section.id, uuid.UUID)
        assert section.book_id == project.id
        assert section.section_type == "dedication"
        assert section.sort_order == 1
        assert section.status == "draft"
        assert section.book == project
        assert section in project.sections

        # 5. Check unique constraint on (book_id, chapter_number)
        duplicate_chapter = Chapter(
            book_id=project.id,
            chapter_number=1,
            title="Duplicate Title",
        )
        session.add(duplicate_chapter)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # 6. Check Cascade Deletes
        session.delete(project)
        session.commit()

        # Core tables should be clean of related data since CASCADE was on delete
        assert session.query(BookRun).filter_by(book_id=project.id).count() == 0
        assert session.query(Chapter).filter_by(book_id=project.id).count() == 0
        assert session.query(BookSection).filter_by(book_id=project.id).count() == 0
