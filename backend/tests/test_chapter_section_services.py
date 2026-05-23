"""
AIuthor Backend Tests — ChapterService and BookSectionService unit tests.

Tests run against in-memory SQLite (same engine used by conftest.py).
All 18 ORM tables are created before the tests and dropped after.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
import app.models  # noqa: F401 — ensure all models are registered on Base

from app.services import (
    BookProjectService,
    ChapterService,
    BookSectionService,
    NotFoundError,
    ConflictError,
)
from app.schemas import (
    BookProjectCreate,
    ChapterCreate,
    ChapterUpdate,
    ChapterInsertRequest,
    BookSectionCreate,
    BookSectionUpdate,
)
from app.schemas.enums import TonePreset


# ── In-memory test engine ─────────────────────────────────────────────────────

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_ENGINE)

_Session = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    """Return a fresh SQLAlchemy session, rolled back after each test."""
    connection = _ENGINE.connect()
    transaction = connection.begin()
    session = _Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_book(db) -> object:
    """Create and return a BookProject."""
    svc = BookProjectService(db)
    return svc.create_book_project(
        BookProjectCreate(
            topic="Introduction to Machine Learning",
            reader_profile="Beginner Python developers",
            genre="Technology",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=10,
        )
    )


def _chapter_create(book_id, number=1, **overrides) -> ChapterCreate:
    defaults = dict(
        book_id=book_id,
        chapter_number=number,
        title="Understanding Neural Networks",
        summary="Core concepts of neural nets",
    )
    defaults.update(overrides)
    return ChapterCreate(**defaults)


def _section_create(book_id, sort_order=0, **overrides) -> BookSectionCreate:
    defaults = dict(
        book_id=book_id,
        section_type="toc",
        sort_order=sort_order,
    )
    defaults.update(overrides)
    return BookSectionCreate(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# ChapterService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestChapterServiceCreate:

    def test_create_chapter_creates_chapter_for_existing_book(self, db):
        """create_chapter persists a Chapter and returns the model."""
        book = _make_book(db)
        svc = ChapterService(db)
        chapter = svc.create_chapter(book.id, _chapter_create(book.id, number=1))

        assert chapter.id is not None
        assert chapter.book_id == book.id
        assert chapter.chapter_number == 1
        assert chapter.title == "Understanding Neural Networks"
        assert chapter.status == "planned"

    def test_create_chapter_for_missing_book_raises_not_found(self, db):
        """create_chapter raises NotFoundError when book does not exist."""
        from uuid import uuid4
        svc = ChapterService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.create_chapter(uuid4(), _chapter_create(uuid4(), number=1))
        assert exc_info.value.code == "book_not_found"

    def test_duplicate_chapter_number_raises_conflict(self, db):
        """create_chapter raises ConflictError on duplicate chapter_number."""
        book = _make_book(db)
        svc = ChapterService(db)
        svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        with pytest.raises(ConflictError) as exc_info:
            svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        assert exc_info.value.code == "duplicate_chapter_number"


class TestChapterServiceGet:

    def test_get_chapter_returns_created_chapter(self, db):
        """get_chapter retrieves the previously created chapter."""
        book = _make_book(db)
        svc = ChapterService(db)
        created = svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        fetched = svc.get_chapter(book.id, created.id)
        assert fetched.id == created.id

    def test_get_chapter_missing_raises_not_found(self, db):
        """get_chapter raises NotFoundError for an unknown UUID."""
        from uuid import uuid4
        book = _make_book(db)
        svc = ChapterService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.get_chapter(book.id, uuid4())
        assert exc_info.value.code == "chapter_not_found"


class TestChapterServiceList:

    def _create_chapters(self, svc, book_id, n=3):
        chapters = []
        for i in range(1, n + 1):
            chapters.append(
                svc.create_chapter(
                    book_id,
                    _chapter_create(book_id, number=i, title=f"Chapter {i}"),
                )
            )
        return chapters

    def test_list_chapters_returns_items_and_total(self, db):
        """list_chapters returns (items, total) tuple."""
        book = _make_book(db)
        svc = ChapterService(db)
        self._create_chapters(svc, book.id, 3)
        items, total = svc.list_chapters(book.id)
        assert len(items) == 3
        assert total == 3

    def test_list_chapters_filters_by_status(self, db):
        """Only chapters matching status are returned."""
        book = _make_book(db)
        svc = ChapterService(db)
        self._create_chapters(svc, book.id, 2)
        ch = svc.create_chapter(
            book.id, _chapter_create(book.id, number=3, title="Special")
        )
        svc.update_chapter(book.id, ch.id, ChapterUpdate(status="drafting"))

        items, total = svc.list_chapters(book.id, status="drafting")
        assert total == 1
        assert items[0].id == ch.id

    def test_list_chapters_search_finds_title(self, db):
        """Search matches the title field."""
        book = _make_book(db)
        svc = ChapterService(db)
        svc.create_chapter(
            book.id,
            _chapter_create(book.id, number=1, title="Deep Learning Dive"),
        )
        svc.create_chapter(
            book.id,
            _chapter_create(book.id, number=2, title="Python Basics"),
        )
        items, total = svc.list_chapters(book.id, search="deep learning")
        assert total == 1
        assert "Deep Learning" in items[0].title


class TestChapterServiceUpdate:

    def test_update_chapter_updates_only_provided_fields(self, db):
        """update_chapter only writes fields set in the payload."""
        book = _make_book(db)
        svc = ChapterService(db)
        chapter = svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        original_title = chapter.title

        updated = svc.update_chapter(
            book.id, chapter.id, ChapterUpdate(summary="New summary text")
        )
        assert updated.summary == "New summary text"
        assert updated.title == original_title  # unchanged


class TestChapterServiceDelete:

    def test_delete_chapter_deletes_chapter(self, db):
        """delete_chapter removes the chapter from the DB."""
        book = _make_book(db)
        svc = ChapterService(db)
        chapter = svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        result = svc.delete_chapter(book.id, chapter.id)
        assert result is True
        with pytest.raises(NotFoundError):
            svc.get_chapter(book.id, chapter.id)

    def test_delete_missing_chapter_raises_not_found(self, db):
        """delete_chapter raises NotFoundError for unknown id."""
        from uuid import uuid4
        book = _make_book(db)
        svc = ChapterService(db)
        with pytest.raises(NotFoundError):
            svc.delete_chapter(book.id, uuid4())


class TestChapterServiceInsert:

    def test_insert_chapter_after_0_inserts_before_chapter_1(self, db):
        """insert_chapter(after_chapter=0) becomes chapter_number=1."""
        book = _make_book(db)
        svc = ChapterService(db)
        # create existing chapter 1
        svc.create_chapter(book.id, _chapter_create(book.id, number=1, title="Old Ch1"))

        inserted = svc.insert_chapter(
            book.id,
            ChapterInsertRequest(
                after_chapter=0,
                title="Brand New Chapter 1",
                purpose="Cover fundamentals before anything else",
            ),
        )
        assert inserted.chapter_number == 1

    def test_insert_chapter_shifts_existing_chapter_numbers(self, db):
        """Chapters at or above insertion point are renumbered +1."""
        book = _make_book(db)
        svc = ChapterService(db)
        ch1 = svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        ch2 = svc.create_chapter(book.id, _chapter_create(book.id, number=2))

        svc.insert_chapter(
            book.id,
            ChapterInsertRequest(
                after_chapter=1,
                title="Inserted Chapter",
                purpose="A new chapter between 1 and 2",
            ),
        )
        # Refresh from DB
        svc.db.refresh(ch1)
        svc.db.refresh(ch2)
        assert ch1.chapter_number == 1   # unchanged
        assert ch2.chapter_number == 3   # shifted by 1

    def test_insert_chapter_marks_repair_required_in_contract(self, db):
        """The inserted chapter has repair_required=True in chapter_contract."""
        book = _make_book(db)
        svc = ChapterService(db)
        inserted = svc.insert_chapter(
            book.id,
            ChapterInsertRequest(
                after_chapter=0,
                title="Test Insert",
                purpose="Testing repair flag",
            ),
        )
        assert inserted.chapter_contract is not None
        assert inserted.chapter_contract.get("repair_required") is True
        assert inserted.chapter_contract.get("inserted") is True

    def test_reorder_chapters_normalizes_numbering(self, db):
        """reorder_chapters compacts gaps after deletions."""
        book = _make_book(db)
        svc = ChapterService(db)
        ch1 = svc.create_chapter(book.id, _chapter_create(book.id, number=1))
        ch3 = svc.create_chapter(book.id, _chapter_create(book.id, number=3))
        ch5 = svc.create_chapter(book.id, _chapter_create(book.id, number=5))

        result = svc.reorder_chapters(book.id)
        numbers = [c.chapter_number for c in result]
        assert numbers == [1, 2, 3]  # 1→1, 3→2, 5→3


# ══════════════════════════════════════════════════════════════════════════════
# BookSectionService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBookSectionServiceCreate:

    def test_create_section_creates_section_for_existing_book(self, db):
        """create_section persists a BookSection."""
        book = _make_book(db)
        svc = BookSectionService(db)
        section = svc.create_section(book.id, _section_create(book.id))

        assert section.id is not None
        assert section.book_id == book.id
        assert section.section_type == "toc"
        assert section.status == "draft"

    def test_create_section_for_missing_book_raises_not_found(self, db):
        """create_section raises NotFoundError when book does not exist."""
        from uuid import uuid4
        fake_id = uuid4()
        svc = BookSectionService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.create_section(fake_id, _section_create(fake_id))
        assert exc_info.value.code == "book_not_found"


class TestBookSectionServiceGet:

    def test_get_section_returns_section(self, db):
        """get_section retrieves the previously created section."""
        book = _make_book(db)
        svc = BookSectionService(db)
        created = svc.create_section(book.id, _section_create(book.id))
        fetched = svc.get_section(book.id, created.id)
        assert fetched.id == created.id

    def test_get_section_missing_raises_not_found(self, db):
        """get_section raises NotFoundError for an unknown UUID."""
        from uuid import uuid4
        book = _make_book(db)
        svc = BookSectionService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.get_section(book.id, uuid4())
        assert exc_info.value.code == "section_not_found"


class TestBookSectionServiceList:

    def test_list_sections_returns_sorted_sections(self, db):
        """list_sections returns sections sorted by sort_order."""
        book = _make_book(db)
        svc = BookSectionService(db)
        svc.create_section(book.id, _section_create(book.id, sort_order=10, section_type="glossary"))
        svc.create_section(book.id, _section_create(book.id, sort_order=5, section_type="toc"))
        sections = svc.list_sections(book.id)
        assert sections[0].sort_order <= sections[1].sort_order

    def test_list_sections_filters_by_section_type(self, db):
        """list_sections filters on section_type."""
        book = _make_book(db)
        svc = BookSectionService(db)
        svc.create_section(book.id, _section_create(book.id, section_type="toc", sort_order=0))
        svc.create_section(book.id, _section_create(book.id, section_type="glossary", sort_order=1))
        sections = svc.list_sections(book.id, section_type="toc")
        assert len(sections) == 1
        assert sections[0].section_type == "toc"


class TestBookSectionServiceUpdate:

    def test_update_section_updates_content(self, db):
        """update_section writes only provided fields."""
        book = _make_book(db)
        svc = BookSectionService(db)
        section = svc.create_section(book.id, _section_create(book.id))
        original_type = section.section_type

        updated = svc.update_section(
            book.id, section.id, BookSectionUpdate(content="Hello world")
        )
        assert updated.content == "Hello world"
        assert updated.section_type == original_type  # unchanged


class TestBookSectionServiceDelete:

    def test_delete_section_deletes_section(self, db):
        """delete_section removes the section."""
        book = _make_book(db)
        svc = BookSectionService(db)
        section = svc.create_section(book.id, _section_create(book.id))
        result = svc.delete_section(book.id, section.id)
        assert result is True
        with pytest.raises(NotFoundError):
            svc.get_section(book.id, section.id)


class TestBookSectionServiceDefaults:

    def test_create_default_structure_creates_required_front_back_matter(self, db):
        """create_default_structure adds all required front and back sections."""
        book = _make_book(db)
        svc = BookSectionService(db)
        sections = svc.create_default_structure(book.id)

        from app.schemas.section import REQUIRED_FRONT_MATTER_SECTIONS, REQUIRED_BACK_MATTER_SECTIONS
        all_required = set(REQUIRED_FRONT_MATTER_SECTIONS + REQUIRED_BACK_MATTER_SECTIONS)
        created_types = {s.section_type for s in sections}
        assert all_required.issubset(created_types)

    def test_create_default_structure_is_idempotent(self, db):
        """Calling create_default_structure twice does not duplicate sections."""
        book = _make_book(db)
        svc = BookSectionService(db)
        first_call = svc.create_default_structure(book.id)
        second_call = svc.create_default_structure(book.id)

        first_types = [s.section_type for s in first_call]
        second_types = [s.section_type for s in second_call]

        # No duplicates in either call
        assert len(first_types) == len(set(first_types))
        assert len(second_types) == len(set(second_types))
        # Counts should match
        assert len(first_types) == len(second_types)

    def test_reorder_sections_normalizes_sort_order(self, db):
        """reorder_sections compacts gaps in sort_order."""
        book = _make_book(db)
        svc = BookSectionService(db)
        svc.create_section(book.id, _section_create(book.id, sort_order=10, section_type="s1"))
        svc.create_section(book.id, _section_create(book.id, sort_order=20, section_type="s2"))
        svc.create_section(book.id, _section_create(book.id, sort_order=30, section_type="s3"))

        result = svc.reorder_sections(book.id)
        orders = [s.sort_order for s in result]
        assert orders == [0, 1, 2]
