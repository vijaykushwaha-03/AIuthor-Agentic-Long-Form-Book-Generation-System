"""
AIuthor Backend Tests — BookProjectService and BookRunService unit tests.

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

from app.services import BookProjectService, BookRunService, NotFoundError
from app.schemas import BookProjectCreate, BookProjectUpdate, BookRunCreate, BookRunUpdate
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


# ── Shared payload factories ──────────────────────────────────────────────────

def _book_create(**overrides) -> BookProjectCreate:
    defaults = dict(
        topic="Introduction to Machine Learning",
        reader_profile="Beginner data scientists with Python background",
        genre="Technology",
        tone=TonePreset.CONVERSATIONAL,
        target_chapters=10,
        words_per_chapter=2000,
    )
    defaults.update(overrides)
    return BookProjectCreate(**defaults)


def _run_create(book_id, **overrides) -> BookRunCreate:
    return BookRunCreate(book_id=book_id, **overrides)


# ══════════════════════════════════════════════════════════════════════════════
# BookProjectService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBookProjectServiceCreate:

    def test_create_book_project_creates_a_book(self, db):
        """create_book_project persists a BookProject and returns the model."""
        svc = BookProjectService(db)
        payload = _book_create()
        book = svc.create_book_project(payload)

        assert book.id is not None
        assert book.topic == "Introduction to Machine Learning"
        assert book.genre == "Technology"
        assert book.tone == "conversational"
        assert book.status == "created"
        assert book.target_chapters == 10
        assert book.words_per_chapter == 2000

    def test_create_book_project_sets_status_created(self, db):
        """Status defaults to 'created' on creation."""
        svc = BookProjectService(db)
        book = svc.create_book_project(_book_create())
        assert book.status == "created"


class TestBookProjectServiceGet:

    def test_get_book_project_returns_created_book(self, db):
        """get_book_project retrieves the previously created project."""
        svc = BookProjectService(db)
        created = svc.create_book_project(_book_create())
        fetched = svc.get_book_project(created.id)
        assert fetched.id == created.id
        assert fetched.topic == created.topic

    def test_get_book_project_missing_raises_not_found(self, db):
        """get_book_project raises NotFoundError for an unknown UUID."""
        svc = BookProjectService(db)
        from uuid import uuid4
        with pytest.raises(NotFoundError) as exc_info:
            svc.get_book_project(uuid4())
        assert exc_info.value.code == "book_not_found"


class TestBookProjectServiceList:

    def _create_books(self, svc, n=3, **overrides):
        books = []
        for i in range(n):
            payload = _book_create(topic=f"Book {i}", **overrides)
            books.append(svc.create_book_project(payload))
        return books

    def test_list_book_projects_returns_items_and_total(self, db):
        """list_book_projects returns (items, total_count) tuple."""
        svc = BookProjectService(db)
        self._create_books(svc, 3)
        items, total = svc.list_book_projects()
        assert len(items) == 3
        assert total == 3

    def test_list_book_projects_filters_by_status(self, db):
        """Only books with matching status are returned."""
        svc = BookProjectService(db)
        self._create_books(svc, 2)
        book = svc.create_book_project(_book_create(topic="Special Book"))
        svc.mark_status(book.id, "planning")

        items, total = svc.list_book_projects(status="planning")
        assert total == 1
        assert items[0].id == book.id

    def test_list_book_projects_filters_by_tone(self, db):
        """Only books with matching tone are returned."""
        svc = BookProjectService(db)
        svc.create_book_project(_book_create(tone=TonePreset.ACADEMIC))
        svc.create_book_project(_book_create(tone=TonePreset.CONVERSATIONAL))

        items, total = svc.list_book_projects(tone="academic")
        assert total == 1
        assert items[0].tone == "academic"

    def test_list_book_projects_search_finds_topic(self, db):
        """Search hits the topic field."""
        svc = BookProjectService(db)
        svc.create_book_project(_book_create(topic="Deep Learning Essentials"))
        svc.create_book_project(_book_create(topic="Python Basics"))

        items, total = svc.list_book_projects(search="deep learning")
        assert total == 1
        assert "Deep Learning" in items[0].topic

    def test_list_book_projects_pagination(self, db):
        """Pagination returns correct slice."""
        svc = BookProjectService(db)
        self._create_books(svc, 5)
        items, total = svc.list_book_projects(page=2, page_size=2)
        assert len(items) == 2
        assert total == 5


class TestBookProjectServiceUpdate:

    def test_update_book_project_updates_only_provided_fields(self, db):
        """update_book_project only writes fields set in the payload."""
        svc = BookProjectService(db)
        book = svc.create_book_project(_book_create())
        original_genre = book.genre

        updated = svc.update_book_project(
            book.id, BookProjectUpdate(topic="Updated Topic")
        )
        assert updated.topic == "Updated Topic"
        assert updated.genre == original_genre  # unchanged

    def test_mark_status_updates_book_status(self, db):
        """mark_status changes only the status field."""
        svc = BookProjectService(db)
        book = svc.create_book_project(_book_create())
        result = svc.mark_status(book.id, "planning")
        assert result.status == "planning"


class TestBookProjectServiceDelete:

    def test_delete_book_project_deletes_book(self, db):
        """delete_book_project removes the project from the DB."""
        svc = BookProjectService(db)
        book = svc.create_book_project(_book_create())
        result = svc.delete_book_project(book.id)
        assert result is True
        with pytest.raises(NotFoundError):
            svc.get_book_project(book.id)

    def test_delete_missing_book_raises_not_found(self, db):
        """delete_book_project raises NotFoundError for unknown id."""
        svc = BookProjectService(db)
        from uuid import uuid4
        with pytest.raises(NotFoundError):
            svc.delete_book_project(uuid4())


# ══════════════════════════════════════════════════════════════════════════════
# BookRunService Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBookRunServiceCreate:

    def _make_book(self, db):
        svc = BookProjectService(db)
        return svc.create_book_project(_book_create())

    def test_create_run_creates_pending_run_for_existing_book(self, db):
        """create_run persists a BookRun with status='pending'."""
        book = self._make_book(db)
        svc = BookRunService(db)
        payload = _run_create(book_id=book.id)
        run = svc.create_run(payload)

        assert run.id is not None
        assert run.book_id == book.id
        assert run.status == "pending"
        assert run.started_at is None

    def test_create_run_for_missing_book_raises_not_found(self, db):
        """create_run raises NotFoundError if the BookProject doesn't exist."""
        from uuid import uuid4
        svc = BookRunService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.create_run(_run_create(book_id=uuid4()))
        assert exc_info.value.code == "book_not_found"


class TestBookRunServiceGet:

    def _make_run(self, db):
        book_svc = BookProjectService(db)
        book = book_svc.create_book_project(_book_create())
        run_svc = BookRunService(db)
        return run_svc.create_run(_run_create(book_id=book.id))

    def test_get_run_returns_created_run(self, db):
        """get_run returns the previously created run."""
        run = self._make_run(db)
        svc = BookRunService(db)
        fetched = svc.get_run(run.id)
        assert fetched.id == run.id

    def test_get_run_missing_raises_not_found(self, db):
        """get_run raises NotFoundError for an unknown UUID."""
        from uuid import uuid4
        svc = BookRunService(db)
        with pytest.raises(NotFoundError) as exc_info:
            svc.get_run(uuid4())
        assert exc_info.value.code == "run_not_found"


class TestBookRunServiceList:

    def _make_book_and_runs(self, db, n=3):
        book_svc = BookProjectService(db)
        book = book_svc.create_book_project(_book_create())
        run_svc = BookRunService(db)
        runs = [run_svc.create_run(_run_create(book_id=book.id)) for _ in range(n)]
        return book, runs, run_svc

    def test_list_runs_for_book_returns_runs_and_total(self, db):
        """list_runs_for_book returns correct items and count."""
        book, _, svc = self._make_book_and_runs(db, 3)
        items, total = svc.list_runs_for_book(book.id)
        assert len(items) == 3
        assert total == 3

    def test_list_runs_for_book_filters_by_status(self, db):
        """Status filter limits returned runs."""
        book, runs, svc = self._make_book_and_runs(db, 2)
        svc.mark_run_started(runs[0].id)

        items, total = svc.list_runs_for_book(book.id, status="running")
        assert total == 1
        assert items[0].id == runs[0].id


class TestBookRunServiceUpdate:

    def _make_run(self, db):
        book_svc = BookProjectService(db)
        book = book_svc.create_book_project(_book_create())
        run_svc = BookRunService(db)
        return book, run_svc.create_run(_run_create(book_id=book.id)), run_svc

    def test_update_run_updates_status_and_current_agent(self, db):
        """update_run applies only provided fields."""
        _, run, svc = self._make_run(db)
        payload = BookRunUpdate(status="running", current_agent="planner")
        updated = svc.update_run(run.id, payload)
        assert updated.status == "running"
        assert updated.current_agent == "planner"

    def test_mark_run_started_sets_running_and_started_at(self, db):
        """mark_run_started sets status='running' and populates started_at."""
        _, run, svc = self._make_run(db)
        result = svc.mark_run_started(run.id)
        assert result.status == "running"
        assert result.started_at is not None

    def test_mark_run_completed_sets_completed_and_completed_at(self, db):
        """mark_run_completed sets status='completed' and populates completed_at."""
        _, run, svc = self._make_run(db)
        result = svc.mark_run_completed(run.id)
        assert result.status == "completed"
        assert result.completed_at is not None
        assert result.current_agent is None

    def test_mark_run_failed_sets_failed_and_error_message(self, db):
        """mark_run_failed records status, completed_at, and error_message."""
        _, run, svc = self._make_run(db)
        result = svc.mark_run_failed(run.id, error_message="OOM error")
        assert result.status == "failed"
        assert result.error_message == "OOM error"
        assert result.completed_at is not None

    def test_update_current_agent_updates_current_agent(self, db):
        """update_current_agent correctly sets current_agent."""
        _, run, svc = self._make_run(db)
        result = svc.update_current_agent(run.id, "writer")
        assert result.current_agent == "writer"
