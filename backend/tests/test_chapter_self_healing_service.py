"""
AIuthor Backend Tests — Chapter Self-Healing Service (Module 8.2).
"""
from __future__ import annotations

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter, BookSection, CallbackIndex, ConceptBible, AgentTrace
from app.workflows.schemas import InsertChapterRepairRequest, StructureRepairItem
from app.services import NotFoundError, ValidationServiceError
from app.services.chapter_self_healing_service import ChapterSelfHealingService
from app.schemas.enums import ChapterStatus, RunStatus


@pytest.fixture
def test_book(db: Session) -> BookProject:
    """Fixture to provision a BookProject record in db."""
    book = BookProject(
        topic="Self-Healing Systems Architecture",
        genre="technical",
        reader_profile="software engineers",
        tone="conversational",
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
        title="Chapter 1: The Resiliency Mandate",
        summary="Why architectures fail.",
        status=ChapterStatus.PLANNED.value,
    )
    ch2 = Chapter(
        book_id=test_book.id,
        chapter_number=2,
        title="Chapter 2: Circuit Breakers & Reorder Safety",
        summary="Dynamic reordering mechanisms.",
        status=ChapterStatus.PLANNED.value,
    )
    db.add(ch1)
    db.add(ch2)
    db.commit()
    db.refresh(ch1)
    db.refresh(ch2)
    return [ch1, ch2]


class TestChapterSelfHealingService:

    def test_insert_repair_creates_book_run_when_missing(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """1. insert repair creates BookRun when missing."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            run_id=None,
            insert_at_chapter_number=2,
            title="A Practical Bridge Between Retrieval and Generation",
            summary="This inserted chapter explains how retrieved context is transformed.",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.run_id is not None
        db_run = db.get(BookRun, resp.run_id)
        assert db_run is not None
        assert db_run.status == RunStatus.COMPLETED.value
        assert db_run.run_metadata.get("module") == "8.2"

    def test_insert_repair_reuses_provided_run_id(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """2. insert repair reuses provided run_id."""
        run = BookRun(book_id=test_book.id, status=RunStatus.PENDING.value)
        db.add(run)
        db.commit()
        db.refresh(run)

        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            run_id=run.id,
            insert_at_chapter_number=2,
            title="A Practical Bridge Between Retrieval and Generation",
            summary="This inserted chapter explains how retrieved context is transformed.",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.run_id == run.id
        db_run = db.get(BookRun, run.id)
        assert db_run.status == RunStatus.COMPLETED.value

    def test_invalid_book_raises_not_found_error(self, db: Session):
        """3. invalid book raises NotFoundError."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=uuid4(),
            insert_at_chapter_number=2,
            title="A Practical Bridge",
            generate_content=False,
        )
        with pytest.raises(NotFoundError) as exc_info:
            svc.repair_inserted_chapter(req)
        assert exc_info.value.code == "book_not_found"

    def test_insert_at_chapter_2_shifts_later_chapters(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """4. insert at chapter 2 shifts later chapters."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Chapter 2: The New Inserted Chapter",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.inserted_chapter_number == 2
        
        # Verify shifted chapters in DB
        ch1 = db.get(Chapter, test_chapters[0].id)
        ch2 = db.get(Chapter, test_chapters[1].id)
        new_ch = db.get(Chapter, resp.inserted_chapter_id)
        
        assert ch1.chapter_number == 1
        assert new_ch.chapter_number == 2
        assert ch2.chapter_number == 3

    def test_chapter_numbering_remains_continuous(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """5. chapter numbering remains continuous."""
        svc = ChapterSelfHealingService(db)
        # Create discontinuity manually
        test_chapters[1].chapter_number = 5
        db.commit()

        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="A Practical Bridge",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        
        all_chapters = (
            db.query(Chapter)
            .filter(Chapter.book_id == test_book.id)
            .order_by(Chapter.chapter_number)
            .all()
        )
        # Verify sequence 1, 2, 3
        assert [ch.chapter_number for ch in all_chapters] == [1, 2, 3]

    def test_inserted_chapter_has_repair_required_metadata(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """6. inserted chapter has repair_required metadata."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="New Segment",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        new_ch = db.get(Chapter, resp.inserted_chapter_id)
        assert new_ch.chapter_contract.get("inserted_via_self_healing") is True
        # Since generate_content=False, it didn't complete RAG workflow repair, so contract remains repair_required=True
        assert new_ch.chapter_contract.get("repair_required") is True

    def test_repair_toc_creates_repair_item(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """7. repair_toc creates repair item."""
        # Create a TOC section
        toc_section = BookSection(
            book_id=test_book.id,
            section_type="toc",
            title="Table of Contents",
            content="# Initial TOC",
            sort_order=1,
            status="draft",
        )
        db.add(toc_section)
        db.commit()
        db.refresh(toc_section)

        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Inserted Chapter 2",
            generate_content=False,
            build_context_pack=False,
            repair_toc=True,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.toc_repaired is True
        
        # Verify Repair Log
        repaired_tocs = [item for item in resp.repair_items if item.item_type == "toc"]
        assert len(repaired_tocs) == 1
        assert repaired_tocs[0].status == "success"
        assert "Inserted Chapter 2" in repaired_tocs[0].after_value

    def test_repair_callbacks_creates_repair_item(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """8. repair_callbacks creates repair item."""
        # Create callback references: cb pointing to chapter 2 targets
        cb1 = CallbackIndex(
            book_id=test_book.id,
            source_chapter=2,
            target_chapter=1,
            concept="Circuit Breaker",
            callback_text="As discussed in chapter 2...",
            status="active",
        )
        db.add(cb1)
        db.commit()
        db.refresh(cb1)

        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Inserted Middle Chapter",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=True,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.callbacks_repaired is True
        
        # Verify db shift: target_chapter=1 (stays), source_chapter=2 shifts to 3
        db.refresh(cb1)
        assert cb1.source_chapter == 3
        assert cb1.target_chapter == 1
        
        # Repair item check
        cb_items = [item for item in resp.repair_items if item.item_type == "callback"]
        assert len(cb_items) >= 1
        assert cb_items[0].status == "success"

    def test_repair_glossary_creates_repair_item(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """9. repair_glossary creates repair item."""
        # Create ConceptBible references
        cp1 = ConceptBible(
            book_id=test_book.id,
            concept="Idempotency",
            definition="Design pattern",
            first_chapter=2,
            appears_in_chapters=[1, 2],
        )
        db.add(cp1)
        db.commit()
        db.refresh(cp1)

        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Inserted Chapter 2",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=True,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.glossary_repaired is True
        
        # Verify ConceptBible shifts: first_chapter 2 shifts to 3. appears_in_chapters: 2 shifts to 3 (so [1, 3])
        db.refresh(cp1)
        assert cp1.first_chapter == 3
        assert cp1.appears_in_chapters == [1, 3]

    def test_repair_back_matter_creates_repair_item(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """10. repair_back_matter creates repair item."""
        # Create back matter section
        glossary_section = BookSection(
            book_id=test_book.id,
            section_type="glossary",
            title="Glossary of Terms",
            content="# Glossary",
            sort_order=10,
            status="draft",
        )
        db.add(glossary_section)
        db.commit()
        db.refresh(glossary_section)

        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Inserted Chapter 2",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=True,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.back_matter_repaired is True
        
        # Verify metadata audit
        db.refresh(glossary_section)
        assert glossary_section.section_metadata is not None
        assert "glossary_repaired_at" in glossary_section.section_metadata
        assert glossary_section.section_metadata["inserted_chapter_id"] == str(resp.inserted_chapter_id)

    def test_generate_content_false_inserts_and_repairs_structure_only(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """11. generate_content=false inserts and repairs structure only."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Structural Only",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        new_ch = db.get(Chapter, resp.inserted_chapter_id)
        assert new_ch.final_text is None
        assert new_ch.status == "drafting"
        assert resp.status == "completed"

    def test_generate_content_true_mock_run_persists_inserted_chapter_content(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """12. generate_content=true mock run persists inserted chapter content."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Chapter 2: Dynamic Execution",
            generate_content=True,
            execution_mode="mock",
            build_context_pack=False,
            traced=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.status == "completed"
        
        new_ch = db.get(Chapter, resp.inserted_chapter_id)
        assert new_ch.status == ChapterStatus.COMPLETED.value
        assert new_ch.final_text is not None
        assert "Assemble a final compact book" in new_ch.final_text
        assert new_ch.chapter_contract.get("repair_required") is False

    def test_book_run_status_becomes_completed_on_success(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """13. BookRun status becomes completed on success."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Success Run",
            generate_content=False,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        db_run = db.get(BookRun, resp.run_id)
        assert db_run.status == RunStatus.COMPLETED.value

    def test_traces_link_to_run_id_book_id_chapter_id(self, db: Session, test_book: BookProject, test_chapters: list[Chapter]):
        """14. traces link to run_id/book_id/chapter_id."""
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Traced Chapter Run",
            generate_content=True,
            execution_mode="mock",
            traced=True,
            persist_traces=True,
            build_context_pack=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.trace_bundle is not None
        
        # Verify trace entities in DB
        traces = db.query(AgentTrace).filter(AgentTrace.run_id == resp.run_id).all()
        assert len(traces) == 8  # Full pipeline has 8 steps/agents
        for t in traces:
            assert t.book_id == test_book.id

    def test_partial_repair_failure_is_recorded_as_repair_item(self, db: Session, test_book: BookProject, test_chapters: list[Chapter], monkeypatch):
        """15. partial repair failure is recorded as repair item."""
        # Monkeypatch _repair_toc to crash
        def mock_repair_toc(book, inserted_chapter, affected_chapters):
            raise RuntimeError("DB Lock/TOC Write Error")
        
        monkeypatch.setattr(ChapterSelfHealingService, "_repair_toc", mock_repair_toc)
        
        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Crash Proof TOC",
            generate_content=False,
            build_context_pack=False,
            repair_toc=True,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        # Check that we handled the failure gracefully, flagged it in repair items, and completed successfully
        assert resp.status == "completed"
        assert resp.toc_repaired is False
        
        failed_tocs = [item for item in resp.repair_items if item.item_type == "toc"]
        assert len(failed_tocs) == 1
        assert failed_tocs[0].status == "failed"
        assert "TOC repair partially failed" in failed_tocs[0].message

    def test_no_gemini_openai_calls_in_tests(self, db: Session, test_book: BookProject, test_chapters: list[Chapter], monkeypatch):
        """16. no Gemini/OpenAI calls in tests."""
        from app.services.agent_execution_service import AgentExecutionService
        def boom_run_once(self, input):
            raise RuntimeError("Real Gemini/OpenAI provider called!")
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        svc = ChapterSelfHealingService(db)
        req = InsertChapterRepairRequest(
            book_id=test_book.id,
            insert_at_chapter_number=2,
            title="Safe Offline Mock Generation",
            generate_content=True,
            execution_mode="mock",
            build_context_pack=False,
            traced=False,
            repair_toc=False,
            repair_callbacks=False,
            repair_glossary=False,
            repair_back_matter=False,
        )
        resp = svc.repair_inserted_chapter(req)
        assert resp.status == "completed"
        new_ch = db.get(Chapter, resp.inserted_chapter_id)
        assert new_ch.status == ChapterStatus.COMPLETED.value
