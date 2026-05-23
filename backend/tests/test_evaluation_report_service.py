"""
AIuthor Backend Tests — Evaluation Report Service (Module 11.0).
"""
from __future__ import annotations

import os
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter, ExportFile, EvalResult
from app.models.memory import FactRegistry, ConceptBible, CharacterBible, CallbackIndex, ToneFingerprint, DecisionLog
from app.models.observability import AgentTrace, PromptLog, TokenCostLedger
from app.services.evaluation_report_service import EvaluationReportService
from app.services.exceptions import NotFoundError
from app.workflows.schemas import EvaluationReportRequest

@pytest.fixture
def eval_book(db: Session) -> BookProject:
    book = BookProject(
        topic="Micro-Frontend Architecture",
        genre="Technical",
        reader_profile="Software Architects",
        tone="professional",
        target_chapters=2,
        project_metadata={"title": "Micro-Frontends Guide", "author": "Vijay Patel"},
        status="created"
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book

def test_generate_report_validates_book_exists(db: Session):
    """1. generate_evaluation_report validates book exists."""
    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=uuid4())
    with pytest.raises(NotFoundError):
        svc.generate_evaluation_report(req)

def test_chapter_checks_pass_with_generated_content(db: Session, eval_book: BookProject):
    """2. chapter checks pass with generated chapter content."""
    # Seed 2 valid chapters
    c1 = Chapter(
        book_id=eval_book.id,
        chapter_number=1,
        title="Introduction",
        final_text="word " * 250,
        status="completed"
    )
    c2 = Chapter(
        book_id=eval_book.id,
        chapter_number=2,
        title="Core Concepts",
        final_text="word " * 250,
        status="completed"
    )
    db.add(c1)
    db.add(c2)
    db.commit()

    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, include_export_checks=False, include_trace_checks=False, include_memory_checks=False, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert res.status == "pass"
    assert res.pass_count >= 5

def test_chapter_checks_fail_on_no_chapters(db: Session, eval_book: BookProject):
    """3. chapter checks fail on no chapters."""
    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, include_export_checks=False, include_trace_checks=False, include_memory_checks=False, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert res.status == "fail"
    fail_items = [c for c in res.checks if c.status == "fail"]
    assert len(fail_items) > 0
    assert any(f.check_name == "chapter_count" for f in fail_items)

def test_export_checks_pass_when_export_file_exists(db: Session, eval_book: BookProject, tmp_path):
    """4. export checks pass when ExportFile exists."""
    dummy_file = tmp_path / "test.docx"
    dummy_file.write_text("dummy docx content")

    ef = ExportFile(
        book_id=eval_book.id,
        export_type="docx",
        file_path=str(dummy_file),
        file_name="test.docx",
        status="ready"
    )
    db.add(ef)
    db.commit()

    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, include_chapter_checks=False, include_export_checks=True, include_trace_checks=False, include_memory_checks=False, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert res.status == "warning" # warn because PDF is missing
    docx_check = next(c for c in res.checks if c.check_name == "docx_export_record")
    integrity_check = next(c for c in res.checks if c.check_name == "export_file_integrity")
    assert docx_check.status == "pass"
    assert integrity_check.status == "pass"

def test_export_checks_warn_when_pdf_failed(db: Session, eval_book: BookProject, tmp_path):
    """5. export checks warn when PDF failed but DOCX exists."""
    dummy_docx = tmp_path / "test.docx"
    dummy_docx.write_text("dummy docx content")

    ef1 = ExportFile(
        book_id=eval_book.id,
        export_type="docx",
        file_path=str(dummy_docx),
        file_name="test.docx",
        status="ready"
    )
    ef2 = ExportFile(
        book_id=eval_book.id,
        export_type="pdf",
        file_path="failed/path.pdf",
        file_name="test.pdf",
        status="failed"
    )
    db.add(ef1)
    db.add(ef2)
    db.commit()

    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, include_chapter_checks=False, include_export_checks=True, include_trace_checks=False, include_memory_checks=False, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert res.status == "warning"
    pdf_check = next(c for c in res.checks if c.check_name == "pdf_export_record")
    assert pdf_check.status == "warning"

def test_trace_checks_detect_8_agent_traces(db: Session, eval_book: BookProject):
    """6. trace checks detect 8-agent traces."""
    run_id = uuid4()
    # Create BookRun
    from app.models import BookRun
    run = BookRun(id=run_id, book_id=eval_book.id, status="completed")
    db.add(run)
    db.commit()

    required_agents = ["planner", "researcher", "writer", "humanizer", "editor", "fact_checker", "memory_keeper", "assembler"]
    for agent in required_agents:
        trace = AgentTrace(
            run_id=run_id,
            book_id=eval_book.id,
            agent_name=agent,
            status="completed"
        )
        db.add(trace)
    
    # Prompt log and ledger
    pl = PromptLog(run_id=run_id, book_id=eval_book.id, agent_name="planner", model_name="gemini", prompt_name="planner_v1", prompt_text="dummy")
    tl = TokenCostLedger(run_id=run_id, book_id=eval_book.id, model_name="gemini", input_tokens=100, output_tokens=50, estimated_cost=0.001)
    db.add(pl)
    db.add(tl)
    db.commit()

    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, run_id=run_id, include_chapter_checks=False, include_export_checks=False, include_trace_checks=True, include_memory_checks=False, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert res.status == "pass"
    coverage = next(c for c in res.checks if c.check_name == "agent_coverage")
    assert coverage.status == "pass"

def test_memory_checks_detect_memory_records(db: Session, eval_book: BookProject):
    """7. memory checks detect memory records."""
    f = FactRegistry(book_id=eval_book.id, claim="React is a library", confidence=1.0, status="verified")
    db.add(f)
    db.commit()

    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, include_chapter_checks=False, include_export_checks=False, include_trace_checks=False, include_memory_checks=True, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert res.status == "pass"
    mem_check = next(c for c in res.checks if c.check_name == "continuity_memory")
    assert mem_check.status == "pass"
    assert mem_check.details["facts_count"] == 1

def test_persists_eval_result_rows(db: Session, eval_book: BookProject):
    """8 & 9. persists EvalResult rows based on flag."""
    c = Chapter(
        book_id=eval_book.id,
        chapter_number=1,
        title="Intro",
        final_text="word " * 250,
        status="completed"
    )
    db.add(c)
    db.commit()

    # 1. Enabled
    svc = EvaluationReportService(db)
    req1 = EvaluationReportRequest(book_id=eval_book.id, include_chapter_checks=True, include_export_checks=False, include_trace_checks=False, include_memory_checks=False, persist_eval_results=True)
    res1 = svc.generate_evaluation_report(req1)
    assert len(res1.persisted_eval_ids) > 0

    db_evals = db.query(EvalResult).filter(EvalResult.book_id == eval_book.id).all()
    assert len(db_evals) == len(res1.persisted_eval_ids)

    # 2. Disabled
    db.query(EvalResult).filter(EvalResult.book_id == eval_book.id).delete()
    db.commit()

    req2 = EvaluationReportRequest(book_id=eval_book.id, include_chapter_checks=True, include_export_checks=False, include_trace_checks=False, include_memory_checks=False, persist_eval_results=False)
    res2 = svc.generate_evaluation_report(req2)
    assert len(res2.persisted_eval_ids) == 0
    assert db.query(EvalResult).filter(EvalResult.book_id == eval_book.id).count() == 0

def test_markdown_report_includes_summary_and_scorecard(db: Session, eval_book: BookProject):
    """10. markdown report includes summary and scorecard."""
    svc = EvaluationReportService(db)
    req = EvaluationReportRequest(book_id=eval_book.id, include_chapter_checks=False, include_export_checks=False, include_trace_checks=False, include_memory_checks=True, persist_eval_results=False)
    res = svc.generate_evaluation_report(req)
    assert "# AIuthor Evaluation Report" in res.markdown_report
    assert "## Scorecard" in res.markdown_report
    assert "## Summary" in res.markdown_report
