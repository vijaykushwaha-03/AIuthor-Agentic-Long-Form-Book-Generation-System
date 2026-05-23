"""
AIuthor Backend Tests — BookRun Workflow Service (Module 8.0).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter, DocumentChunk, AgentTrace
from app.schemas.chapter import ChapterCreate
from app.workflows.schemas import BookRunWorkflowRequest
from app.services import BookProjectService, ChapterService, BookRunWorkflowService, NotFoundError
from app.workflows.exceptions import WorkflowExecutionError


@pytest.fixture
def test_book(db: Session) -> BookProject:
    """Fixture to provision a BookProject record in db."""
    book = BookProject(
        topic="Microservices architecture principles",
        genre="technical",
        reader_profile="software developers",
        tone="instructive",
        target_chapters=3,
        status="created",
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@pytest.fixture
def test_chapter(db: Session, test_book: BookProject) -> Chapter:
    """Fixture to provision a Chapter record under test_book in db."""
    chapter = Chapter(
        book_id=test_book.id,
        chapter_number=1,
        title="Introduction to Microservices",
        summary="Overview of architectural patterns",
        status="planned",
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


class TestBookRunWorkflowService:

    def test_run_book_workflow_creates_run_if_missing(self, db: Session, test_book: BookProject):
        """1. run_book_workflow creates BookRun when run_id is missing."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)
        assert resp.run_id is not None

        db_run = db.get(BookRun, resp.run_id)
        assert db_run is not None
        assert db_run.status == "completed"

    def test_run_book_workflow_reuses_provided_run_id(self, db: Session, test_book: BookProject):
        """2. run_book_workflow reuses provided run_id."""
        run = BookRun(
            book_id=test_book.id,
            status="pending",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=run.id,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)
        assert resp.run_id == run.id

        db_run = db.get(BookRun, run.id)
        assert db_run.status == "completed"

    def test_run_book_workflow_validates_book_exists(self, db: Session):
        """3. run_book_workflow validates book exists."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=uuid4(),  # Non-existent book ID
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(NotFoundError) as exc_info:
            svc.run_book_workflow(req)
        assert exc_info.value.code == "book_not_found"

    def test_run_book_workflow_validates_run_belongs_to_book(self, db: Session, test_book: BookProject):
        """4. run_book_workflow validates run belongs to book."""
        # Create a run belonging to a different book project
        other_book = BookProject(
            topic="Other topic",
            genre="other",
            reader_profile="other",
            tone="other",
            target_chapters=3,
        )
        db.add(other_book)
        db.commit()
        db.refresh(other_book)

        other_run = BookRun(
            book_id=other_book.id,
            status="pending",
        )
        db.add(other_run)
        db.commit()
        db.refresh(other_run)

        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,  # Original book project
            run_id=other_run.id,  # Run belonging to other book project
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(NotFoundError) as exc_info:
            svc.run_book_workflow(req)
        assert exc_info.value.code == "run_book_mismatch"

    def test_run_book_workflow_validates_chapter_belongs_to_book(self, db: Session, test_book: BookProject):
        """5. run_book_workflow validates chapter belongs to book."""
        # Create another book and a chapter belonging to that other book
        other_book = BookProject(
            topic="Other topic",
            genre="other",
            reader_profile="other",
            tone="other",
            target_chapters=3,
        )
        db.add(other_book)
        db.commit()
        db.refresh(other_book)

        other_chapter = Chapter(
            book_id=other_book.id,
            chapter_number=1,
            title="Other Chapter",
            summary="Other summary",
            status="planned",
        )
        db.add(other_chapter)
        db.commit()
        db.refresh(other_chapter)

        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,  # Original book
            run_id=None,
            chapter_id=other_chapter.id,  # Chapter belonging to other book
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(NotFoundError) as exc_info:
            svc.run_book_workflow(req)
        assert exc_info.value.code == "chapter_not_found"

    def test_mock_traced_run_returns_workflow_output(self, db: Session, test_book: BookProject):
        """6. mock traced run returns workflow output."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=True,
            persist_traces=True,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)
        assert resp.status == "completed"
        assert resp.traced is True
        assert resp.workflow_output is not None
        assert "steps" in resp.workflow_output
        assert len(resp.workflow_output["steps"]) == 5
        assert resp.trace_bundle is not None

    def test_mock_traced_run_persists_trace_rows(self, db: Session, test_book: BookProject):
        """7. mock traced run persists trace rows."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=True,
            persist_traces=True,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)

        traces = db.query(AgentTrace).filter(AgentTrace.run_id == resp.run_id).all()
        assert len(traces) == 5
        for t in traces:
            assert t.book_id == test_book.id
            assert t.status == "completed"

    def test_mock_non_traced_run_works(self, db: Session, test_book: BookProject):
        """8. mock non-traced run works."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)
        assert resp.status == "completed"
        assert resp.traced is False
        assert resp.trace_bundle is None

    def test_build_context_pack_false_skips_retrieval(self, db: Session, test_book: BookProject, monkeypatch):
        """9. build_context_pack false skips retrieval."""
        call_count = {"count": 0}

        from app.services.context_pack_service import ContextPackService
        original_build = ContextPackService.build_context_pack

        def mock_build(self, request):
            call_count["count"] += 1
            return original_build(self, request)

        monkeypatch.setattr(ContextPackService, "build_context_pack", mock_build)

        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,  # Build is false → skips
        )
        resp = svc.run_book_workflow(req)
        assert resp.context_pack is None
        assert call_count["count"] == 0

    def test_empty_context_pack_does_not_fail_workflow(self, db: Session, test_book: BookProject):
        """10. empty context pack does not fail workflow."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=True,  # Build is true, but database has zero chunks
        )
        resp = svc.run_book_workflow(req)
        assert resp.status == "completed"
        assert resp.context_pack is not None
        assert resp.context_pack["total_chunks"] == 0
        assert "note" in resp.context_pack["metadata"]
        assert "No context chunks found. Workflow ran without RAG context." in resp.context_pack["metadata"]["note"]

    def test_successful_workflow_marks_run_completed(self, db: Session, test_book: BookProject):
        """11. successful workflow marks run completed."""
        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)

        db_run = db.get(BookRun, resp.run_id)
        assert db_run.status == "completed"
        assert db_run.completed_at is not None
        assert db_run.error_message is None

    def test_failed_workflow_marks_run_failed(self, db: Session, test_book: BookProject, monkeypatch):
        """12. failed workflow marks run failed."""
        from app.services.workflow_execution_service import WorkflowExecutionService
        def boom_run(self, input):
            raise RuntimeError("LangGraph execution crashed")
        monkeypatch.setattr(WorkflowExecutionService, "run_workflow_mock", boom_run)

        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(Exception) as exc_info:
            svc.run_book_workflow(req)
        assert "LangGraph execution crashed" in str(exc_info.value)

        # Run id should have been created and marked as failed
        runs = db.query(BookRun).filter(BookRun.book_id == test_book.id).all()
        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert runs[0].error_message is not None
        assert "LangGraph execution crashed" in runs[0].error_message

    def test_no_gemini_openai_calls_in_tests(self, db: Session, test_book: BookProject, monkeypatch):
        """13. no Gemini/OpenAI calls in tests."""
        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, input):
            raise RuntimeError("Real Gemini/OpenAI provider called!")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        svc = BookRunWorkflowService(db)
        req = BookRunWorkflowRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="mini_book_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.run_book_workflow(req)
        assert resp.status == "completed"
        # Restore
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)
