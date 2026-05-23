"""
AIuthor Backend Tests — Chapter Generation Loop Service (Module 8.1).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter, AgentTrace
from app.workflows.schemas import ChapterGenerationRequest
from app.services import BookProjectService, ChapterService, NotFoundError, ValidationServiceError
from app.services.chapter_generation_service import ChapterGenerationService
from app.schemas.chapter import ChapterCreate
from app.schemas.enums import ChapterStatus, RunStatus


@pytest.fixture
def test_book(db: Session) -> BookProject:
    """Fixture to provision a BookProject record in db."""
    book = BookProject(
        topic="Introduction to Advanced Agentic AI systems",
        genre="technical",
        reader_profile="engineers",
        tone="instructive",
        target_chapters=3,
        status="created",
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@pytest.fixture
def test_chapters(db: Session, test_book: BookProject) -> list[Chapter]:
    """Fixture to provision a Chapter list under test_book in db."""
    ch1 = Chapter(
        book_id=test_book.id,
        chapter_number=1,
        title="Chapter 1: Agentic Orchestration Fundamentals",
        summary="Overview of agents",
        status=ChapterStatus.PLANNED.value,
    )
    ch2 = Chapter(
        book_id=test_book.id,
        chapter_number=2,
        title="Chapter 2: Context Pack and Hybrid Retrieval RAG",
        summary="RAG systems explanation",
        status=ChapterStatus.PLANNED.value,
    )
    db.add(ch1)
    db.add(ch2)
    db.commit()
    db.refresh(ch1)
    db.refresh(ch2)
    return [ch1, ch2]


class TestChapterGenerationService:

    def test_generate_chapters_creates_run_if_missing(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """1. generate_chapters creates BookRun when missing."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            run_id=None,
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.run_id is not None
        db_run = db.get(BookRun, resp.run_id)
        assert db_run is not None
        assert db_run.status == RunStatus.COMPLETED.value

    def test_generate_chapters_reuses_run_id(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """2. generate_chapters reuses run_id."""
        run = BookRun(book_id=test_book.id, status=RunStatus.PENDING.value)
        db.add(run)
        db.commit()
        db.refresh(run)

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            run_id=run.id,
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.run_id == run.id
        db_run = db.get(BookRun, run.id)
        assert db_run.status == RunStatus.COMPLETED.value

    def test_generate_chapters_invalid_book_raises_not_found(self, db: Session):
        """3. invalid book raises NotFoundError."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=uuid4(),
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(NotFoundError) as exc_info:
            svc.generate_chapters(req)
        assert exc_info.value.code == "book_not_found"

    def test_generate_chapters_run_book_mismatch_raises_validation(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """4. invalid run/book mismatch raises ValidationServiceError."""
        other_book = BookProject(
            topic="Other topic",
            genre="technical",
            reader_profile="engineers",
            tone="instructive",
            target_chapters=1,
            status="created",
        )
        db.add(other_book)
        db.commit()
        db.refresh(other_book)

        other_run = BookRun(book_id=other_book.id, status=RunStatus.PENDING.value)
        db.add(other_run)
        db.commit()
        db.refresh(other_run)

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            run_id=other_run.id,
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(ValidationServiceError) as exc_info:
            svc.generate_chapters(req)
        assert exc_info.value.code == "run_book_mismatch"

    def test_generate_chapters_chapter_book_mismatch_raises_validation(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """5. invalid chapter/book mismatch raises ValidationServiceError."""
        other_book = BookProject(
            topic="Other topic",
            genre="technical",
            reader_profile="engineers",
            tone="instructive",
            target_chapters=1,
            status="created",
        )
        db.add(other_book)
        db.commit()
        db.refresh(other_book)

        other_chapter = Chapter(book_id=other_book.id, chapter_number=1, title="Other", status=ChapterStatus.PLANNED.value)
        db.add(other_chapter)
        db.commit()
        db.refresh(other_chapter)

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[other_chapter.id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        with pytest.raises(ValidationServiceError) as exc_info:
            svc.generate_chapters(req)
        assert exc_info.value.code == "chapter_book_mismatch"

    def test_select_chapters_by_chapter_ids(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """6. selects chapters by chapter_ids."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[1].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
        )
        ch_list = svc._select_chapters(req)
        assert len(ch_list) == 1
        assert ch_list[0].id == test_chapters[1].id

    def test_select_chapters_by_chapter_numbers(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """7. selects chapters by chapter_numbers."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_numbers=[2],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
        )
        ch_list = svc._select_chapters(req)
        assert len(ch_list) == 1
        assert ch_list[0].chapter_number == 2

    def test_select_all_chapters_when_no_filters(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """8. selects all chapters when no filters provided."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
        )
        ch_list = svc._select_chapters(req)
        assert len(ch_list) == 2

    def test_max_chapters_limits_selected_chapters(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """9. max_chapters limits selected chapters."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            max_chapters=1,
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.total_requested == 1
        assert len(resp.chapters) == 1

    def test_mock_traced_generation_returns_response(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """10. mock traced generation returns response."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=True,
            persist_traces=True,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.traced is True
        assert resp.completed_count == 1
        assert resp.trace_bundle is not None
        assert len(resp.chapters) == 1
        assert resp.chapters[0].trace_count == 8

    def test_mock_non_traced_generation_works(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """11. mock non-traced generation works."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.traced is False
        assert resp.trace_bundle is None
        assert resp.completed_count == 1

    def test_generated_content_is_persisted_to_chapter(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """12. generated content is persisted to chapter."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        ch = db.get(Chapter, test_chapters[0].id)
        assert ch.draft_text is not None
        assert ch.final_text is not None
        assert "Assemble a final compact book" in ch.final_text


    def test_chapter_status_becomes_completed(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """13. chapter status becomes completed."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        svc.generate_chapters(req)
        ch = db.get(Chapter, test_chapters[0].id)
        assert ch.status == ChapterStatus.COMPLETED.value

    def test_book_run_status_becomes_completed(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """14. BookRun status becomes completed."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        db_run = db.get(BookRun, resp.run_id)
        assert db_run.status == RunStatus.COMPLETED.value

    def test_book_run_progress_reaches_100(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """15. BookRun progress reaches 100."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        db_run = db.get(BookRun, resp.run_id)
        assert db_run.run_metadata.get("progress_percentage") == 100.0

    def test_overwrite_existing_false_skips_existing(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """16. overwrite_existing=False skips existing generated chapter."""
        # Setup existing content
        test_chapters[0].final_text = "Pre-existing content"
        db.commit()

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            overwrite_existing=False,
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.skipped_count == 1
        assert resp.completed_count == 0
        ch = db.get(Chapter, test_chapters[0].id)
        assert ch.final_text == "Pre-existing content"

    def test_overwrite_existing_true_regenerates(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """17. overwrite_existing=True regenerates existing chapter."""
        # Setup existing content
        test_chapters[0].final_text = "Pre-existing content"
        db.commit()

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            overwrite_existing=True,
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.skipped_count == 0
        assert resp.completed_count == 1
        ch = db.get(Chapter, test_chapters[0].id)
        assert ch.final_text != "Pre-existing content"
        assert "Assemble a final compact book" in ch.final_text


    def test_empty_context_pack_does_not_fail(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """18. empty context pack does not fail."""
        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=True,  # Database has zero chunks → empty RAG context pack built
        )
        resp = svc.generate_chapters(req)
        assert resp.completed_count == 1
        ch = db.get(Chapter, test_chapters[0].id)
        assert ch.status == ChapterStatus.COMPLETED.value

    def test_failed_chapter_marks_chapter_failed_and_continues(self, db: Session, test_book: BookProject, test_chapters: list[Chapter], monkeypatch):
        """19. failed chapter marks chapter failed and continues."""
        from app.services.workflow_execution_service import WorkflowExecutionService
        def boom_run(self, input):
            raise RuntimeError("LangGraph execution crashed")
        monkeypatch.setattr(WorkflowExecutionService, "run_workflow_mock", boom_run)

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id, test_chapters[1].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.failed_count == 2
        ch1 = db.get(Chapter, test_chapters[0].id)
        ch2 = db.get(Chapter, test_chapters[1].id)
        assert ch1.status == ChapterStatus.FAILED.value
        assert ch2.status == ChapterStatus.FAILED.value

    def test_no_gemini_openai_calls_in_tests(self, db: Session, test_book: BookProject, test_chapters: list[Chapter], monkeypatch):
        """20. no Gemini/OpenAI calls in tests."""
        from app.services.agent_execution_service import AgentExecutionService
        def boom_run_once(self, input):
            raise RuntimeError("Real Gemini/OpenAI provider called!")
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        svc = ChapterGenerationService(db)
        req = ChapterGenerationRequest(
            book_id=test_book.id,
            chapter_ids=[test_chapters[0].id],
            workflow_name="full_agent_pipeline",
            execution_mode="mock",
            traced=False,
            build_context_pack=False,
        )
        resp = svc.generate_chapters(req)
        assert resp.completed_count == 1
        ch = db.get(Chapter, test_chapters[0].id)
        assert ch.status == ChapterStatus.COMPLETED.value
