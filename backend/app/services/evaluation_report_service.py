"""
AIuthor Backend — Evaluation Report Service.
Runs evaluation checks on book structures, chapters, memory registries, and logs.
"""
from __future__ import annotations

import os
from uuid import UUID
import logging
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter, BookSection, ExportFile
from app.models.memory import FactRegistry, ConceptBible, CharacterBible, CallbackIndex, ToneFingerprint, DecisionLog
from app.models.observability import AgentTrace, PromptLog, TokenCostLedger
from app.services.exceptions import NotFoundError
from app.services.eval_service import EvalService
from app.services.book_assembler_service import BookAssemblerService
from app.services.export_service import ExportService
from app.services.memory_service import MemoryService
from app.services.workflow_observability_service import WorkflowObservabilityService

from app.workflows.schemas import (
    EvaluationReportRequest,
    EvaluationCheckItem,
    EvaluationReportResponse,
)
from app.schemas.eval import EvalResultCreate

logger = logging.getLogger(__name__)

class EvaluationReportService:
    """
    Coordinates and persists qualitative book project evaluation results.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.eval_service = EvalService(db)
        self.assembler = BookAssemblerService(db)
        self.export_service = ExportService(db)
        self.memory_service = MemoryService(db)
        self.workflow_observability_service = WorkflowObservabilityService(db)

    def _check_book_exists(self, book_id: UUID) -> BookProject:
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message=f"Book project with ID {book_id} not found.",
                code="book_not_found",
                details={"book_id": str(book_id)}
            )
        return book

    def _check_chapters(self, book_id: UUID) -> list[EvaluationCheckItem]:
        checks = []
        chapters = (
            self.db.query(Chapter)
            .filter(Chapter.book_id == book_id)
            .order_by(Chapter.chapter_number.asc())
            .all()
        )

        # Check 1: At least one chapter exists
        if not chapters:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_count",
                    status="fail",
                    score=0.0,
                    message="No chapters exist in the book project.",
                    details={"chapter_count": 0}
                )
            )
            return checks
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_count",
                    status="pass",
                    score=1.0,
                    message=f"Book project contains {len(chapters)} chapter(s).",
                    details={"chapter_count": len(chapters)}
                )
            )

        # Check 2: Chapters are sequentially numbered
        nums = [c.chapter_number for c in chapters]
        expected_nums = list(range(1, len(chapters) + 1))
        if nums != expected_nums:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_numbering",
                    status="fail",
                    score=0.0,
                    message=f"Chapter numbering is non-sequential. Expected {expected_nums}, got {nums}.",
                    details={"expected": expected_nums, "actual": nums}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_numbering",
                    status="pass",
                    score=1.0,
                    message="Chapter numbers are sequential and start at 1.",
                    details={"sequence": nums}
                )
            )

        # Check 3: At least one chapter has generated content
        has_generated = any(c.final_text or c.draft_text or c.humanized_text or c.edited_text for c in chapters)
        if not has_generated:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_content_presence",
                    status="fail",
                    score=0.0,
                    message="No chapters have generated content.",
                    details={}
                )
            )
        else:
            missing_final = [c.chapter_number for c in chapters if not c.final_text]
            if missing_final:
                checks.append(
                    EvaluationCheckItem(
                        check_name="chapter_content_presence",
                        status="warning",
                        score=0.5,
                        message=f"Some chapters have content but lack final_text. Chapters: {missing_final}",
                        details={"missing_final_chapters": missing_final}
                    )
                )
            else:
                checks.append(
                    EvaluationCheckItem(
                        check_name="chapter_content_presence",
                        status="pass",
                        score=1.0,
                        message="All chapters have generated final_text.",
                        details={}
                    )
                )

        # Check 4: No chapter has failed status
        failed_chapters = [c.chapter_number for c in chapters if c.status == "failed"]
        if failed_chapters:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_statuses",
                    status="fail",
                    score=0.0,
                    message=f"Chapters {failed_chapters} have a failed status.",
                    details={"failed_chapters": failed_chapters}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_statuses",
                    status="pass",
                    score=1.0,
                    message="No chapters are in failed status.",
                    details={}
                )
            )

        # Check 5: Word count is reasonable
        total_words = 0
        low_word_count_chapters = []
        for c in chapters:
            text = c.final_text or c.draft_text or c.humanized_text or c.edited_text or ""
            words = len(text.split())
            total_words += words
            if words < 200:
                low_word_count_chapters.append((c.chapter_number, words))

        if total_words == 0:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_word_count",
                    status="warning",
                    score=0.0,
                    message="Total book word count is 0.",
                    details={"total_words": 0}
                )
            )
        elif low_word_count_chapters:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_word_count",
                    status="warning",
                    score=0.7,
                    message=f"Total word count is {total_words}, but some chapters are extremely short (< 200 words): {low_word_count_chapters}",
                    details={"total_words": total_words, "short_chapters": low_word_count_chapters}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_word_count",
                    status="pass",
                    score=1.0,
                    message=f"Total word count is {total_words}. All chapters meet minimum word count requirements.",
                    details={"total_words": total_words}
                )
            )

        # Check 6: Insert-repair metadata exists if inserted chapter was tested
        sections = self.db.query(BookSection).filter(BookSection.book_id == book_id).all()
        has_repair_metadata = any(
            c.chapter_contract and "callback_repair" in c.chapter_contract
            for c in chapters
        ) or any(
            s.section_metadata and "inserted_chapter_id" in s.section_metadata
            for s in sections
        )

        if has_repair_metadata:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_repair_metadata",
                    status="pass",
                    score=1.0,
                    message="Insert-repair metadata is present, indicating successful healing/repair logs.",
                    details={}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="chapter_repair_metadata",
                    status="skipped",
                    score=None,
                    message="No insert-repair operations detected or metadata not set.",
                    details={}
                )
            )

        return checks

    def _check_exports(self, book_id: UUID, run_id: UUID | None = None) -> list[EvaluationCheckItem]:
        checks = []
        query = self.db.query(ExportFile).filter(ExportFile.book_id == book_id)
        if run_id is not None:
            query = query.filter(ExportFile.run_id == run_id)
        exports = query.all()

        # Check 1: At least one DOCX export record exists
        docx_exports = [e for e in exports if e.export_type == "docx"]
        if not docx_exports:
            checks.append(
                EvaluationCheckItem(
                    check_name="docx_export_record",
                    status="fail",
                    score=0.0,
                    message="No DOCX export record exists.",
                    details={}
                )
            )
        else:
            failed_docx = [d for d in docx_exports if d.status == "failed"]
            if len(failed_docx) == len(docx_exports):
                checks.append(
                    EvaluationCheckItem(
                        check_name="docx_export_record",
                        status="fail",
                        score=0.0,
                        message="All DOCX export operations failed.",
                        details={}
                    )
                )
            else:
                checks.append(
                    EvaluationCheckItem(
                        check_name="docx_export_record",
                        status="pass",
                        score=1.0,
                        message="Valid DOCX export record exists.",
                        details={}
                    )
                )

        # Check 2: Export file exists on disk when path available
        missing_files = []
        for e in exports:
            if e.status == "ready" and e.file_path:
                if not os.path.exists(e.file_path):
                    missing_files.append(e.file_name)

        if missing_files:
            checks.append(
                EvaluationCheckItem(
                    check_name="export_file_integrity",
                    status="fail",
                    score=0.0,
                    message=f"Exported files are missing from disk: {missing_files}",
                    details={"missing_files": missing_files}
                )
            )
        elif exports:
            checks.append(
                EvaluationCheckItem(
                    check_name="export_file_integrity",
                    status="pass",
                    score=1.0,
                    message="All exported files successfully found on disk.",
                    details={}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="export_file_integrity",
                    status="skipped",
                    score=None,
                    message="No export files to verify on disk.",
                    details={}
                )
            )

        # Check 3: PDF export record exists if generated
        pdf_exports = [e for e in exports if e.export_type == "pdf"]
        if pdf_exports:
            failed_pdf = [p for p in pdf_exports if p.status == "failed"]
            if len(failed_pdf) == len(pdf_exports):
                checks.append(
                    EvaluationCheckItem(
                        check_name="pdf_export_record",
                        status="warning",
                        score=0.5,
                        message="PDF export failed, but DOCX is available.",
                        details={}
                    )
                )
            else:
                checks.append(
                    EvaluationCheckItem(
                        check_name="pdf_export_record",
                        status="pass",
                        score=1.0,
                        message="PDF export is ready and available.",
                        details={}
                    )
                )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="pdf_export_record",
                    status="warning",
                    score=0.0,
                    message="No PDF export record found.",
                    details={}
                )
            )

        return checks

    def _check_traces(self, book_id: UUID, run_id: UUID | None = None) -> list[EvaluationCheckItem]:
        checks = []
        trace_query = self.db.query(AgentTrace).filter(AgentTrace.book_id == book_id)
        if run_id is not None:
            trace_query = trace_query.filter(AgentTrace.run_id == run_id)
        traces = trace_query.all()

        # Check 1: Agent traces exist
        if not traces:
            if run_id is not None:
                checks.append(
                    EvaluationCheckItem(
                        check_name="agent_traces_presence",
                        status="fail",
                        score=0.0,
                        message="No agent traces found for the specified run.",
                        details={"run_id": str(run_id)}
                    )
                )
            else:
                checks.append(
                    EvaluationCheckItem(
                        check_name="agent_traces_presence",
                        status="warning",
                        score=0.0,
                        message="No agent traces found for the book project.",
                        details={}
                    )
                )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="agent_traces_presence",
                    status="pass",
                    score=1.0,
                    message=f"Found {len(traces)} agent trace execution steps.",
                    details={"trace_count": len(traces)}
                )
            )

        # Check 2: Full 8-agent workflow traces include all required agents if available
        if traces:
            agent_names_in_traces = {t.agent_name for t in traces if t.agent_name}
            required_agents = {"planner", "researcher", "writer", "humanizer", "editor", "fact_checker", "memory_keeper", "assembler"}
            missing_agents = required_agents - agent_names_in_traces

            if missing_agents:
                checks.append(
                    EvaluationCheckItem(
                        check_name="agent_coverage",
                        status="warning",
                        score=float(len(required_agents - missing_agents)) / len(required_agents),
                        message=f"Not all 8 agents are present in traces. Missing agents: {list(missing_agents)}.",
                        details={"missing_agents": list(missing_agents), "present_agents": list(agent_names_in_traces)}
                    )
                )
            else:
                checks.append(
                    EvaluationCheckItem(
                        check_name="agent_coverage",
                        status="pass",
                        score=1.0,
                        message="All 8 agents have executed and logged traces successfully.",
                        details={"present_agents": list(agent_names_in_traces)}
                    )
                )

        # Check 3: Prompt logs exist
        prompt_query = self.db.query(PromptLog).filter(PromptLog.book_id == book_id)
        if run_id is not None:
            prompt_query = prompt_query.filter(PromptLog.run_id == run_id)
        prompt_count = prompt_query.count()

        if prompt_count == 0:
            checks.append(
                EvaluationCheckItem(
                    check_name="prompt_logs_presence",
                    status="warning",
                    score=0.0,
                    message="No prompt logs found in database.",
                    details={}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="prompt_logs_presence",
                    status="pass",
                    score=1.0,
                    message=f"Found {prompt_count} prompt logs in the database.",
                    details={"prompt_log_count": prompt_count}
                )
            )

        # Check 4: Token/cost ledger is present
        ledger_query = self.db.query(TokenCostLedger).filter(TokenCostLedger.book_id == book_id)
        if run_id is not None:
            ledger_query = ledger_query.filter(TokenCostLedger.run_id == run_id)
        ledger_count = ledger_query.count()

        if ledger_count == 0:
            checks.append(
                EvaluationCheckItem(
                    check_name="token_ledger_presence",
                    status="warning",
                    score=0.0,
                    message="No token ledger or billing costs recorded in database.",
                    details={}
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="token_ledger_presence",
                    status="pass",
                    score=1.0,
                    message=f"Found {ledger_count} billing or token cost entries in database.",
                    details={"ledger_count": ledger_count}
                )
            )

        return checks

    def _check_memory(self, book_id: UUID) -> list[EvaluationCheckItem]:
        checks = []
        facts_count = self.db.query(FactRegistry).filter(FactRegistry.book_id == book_id).count()
        concepts_count = self.db.query(ConceptBible).filter(ConceptBible.book_id == book_id).count()
        characters_count = self.db.query(CharacterBible).filter(CharacterBible.book_id == book_id).count()
        callbacks_count = self.db.query(CallbackIndex).filter(CallbackIndex.book_id == book_id).count()
        tone_count = self.db.query(ToneFingerprint).filter(ToneFingerprint.book_id == book_id).count()
        decisions_count = self.db.query(DecisionLog).filter(DecisionLog.book_id == book_id).count()

        total_memory_items = facts_count + concepts_count + characters_count + callbacks_count + tone_count + decisions_count

        details = {
            "facts_count": facts_count,
            "concepts_count": concepts_count,
            "characters_count": characters_count,
            "callbacks_count": callbacks_count,
            "tone_count": tone_count,
            "decisions_count": decisions_count,
        }

        if total_memory_items == 0:
            checks.append(
                EvaluationCheckItem(
                    check_name="continuity_memory",
                    status="warning",
                    score=0.0,
                    message="Memory lists are completely empty. Continuity cannot be verified.",
                    details=details
                )
            )
        else:
            checks.append(
                EvaluationCheckItem(
                    check_name="continuity_memory",
                    status="pass",
                    score=1.0,
                    message=f"Continuity memory populated with {total_memory_items} total records across tables.",
                    details=details
                )
            )

        return checks

    def _build_markdown_report(self, book_id: UUID, run_id: UUID | None, checks: list[EvaluationCheckItem]) -> str:
        lines = []
        lines.append("# AIuthor Evaluation Report\n")

        # Summary
        lines.append("## Summary")
        lines.append(f"- **Book Project ID**: `{book_id}`")
        if run_id:
            lines.append(f"- **Workflow Run ID**: `{run_id}`")

        total = len(checks)
        passed = sum(1 for c in checks if c.status == "pass")
        warning = sum(1 for c in checks if c.status == "warning")
        failed = sum(1 for c in checks if c.status == "fail")
        skipped = sum(1 for c in checks if c.status == "skipped")

        overall_status = "pass"
        if failed > 0:
            overall_status = "fail"
        elif warning > 0:
            overall_status = "warning"

        lines.append(f"- **Overall Status**: **{overall_status.upper()}**")
        lines.append(f"- **Total Checks Evaluated**: {total}")
        lines.append(f"- **Passed Checks**: {passed}")
        lines.append(f"- **Warnings**: {warning}")
        lines.append(f"- **Failures**: {failed}")
        lines.append(f"- **Skipped Checks**: {skipped}\n")

        # Scorecard
        lines.append("## Scorecard")
        lines.append("| Check Name | Status | Score | Message |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for c in checks:
            score_val = f"{c.score:.2f}" if c.score is not None else "N/A"
            lines.append(f"| {c.check_name} | {c.status.upper()} | {score_val} | {c.message} |")
        lines.append("")

        # Sections
        lines.append("## Chapter Checks")
        ch_checks = [c for c in checks if c.check_name.startswith("chapter_")]
        if ch_checks:
            for c in ch_checks:
                lines.append(f"- **{c.check_name}** ({c.status.upper()}): {c.message}")
        else:
            lines.append("No chapter checks executed.")
        lines.append("")

        lines.append("## Export Checks")
        exp_checks = [c for c in checks if "export" in c.check_name]
        if exp_checks:
            for c in exp_checks:
                lines.append(f"- **{c.check_name}** ({c.status.upper()}): {c.message}")
        else:
            lines.append("No export checks executed.")
        lines.append("")

        lines.append("## Trace Checks")
        tr_checks = [c for c in checks if "trace" in c.check_name or "ledger" in c.check_name or "logs" in c.check_name]
        if tr_checks:
            for c in tr_checks:
                lines.append(f"- **{c.check_name}** ({c.status.upper()}): {c.message}")
        else:
            lines.append("No trace checks executed.")
        lines.append("")

        lines.append("## Memory Checks")
        mem_checks = [c for c in checks if "memory" in c.check_name or "continuity" in c.check_name]
        if mem_checks:
            for c in mem_checks:
                lines.append(f"- **{c.check_name}** ({c.status.upper()}): {c.message}")
        else:
            lines.append("No memory checks executed.")
        lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        if failed > 0:
            lines.append("> [!CAUTION]")
            lines.append("> Critical failures detected. Please address chapter numbering, missing files, or missing structural requirements before finalizing delivery.")
        elif warning > 0:
            lines.append("> [!WARNING]")
            lines.append("> Warnings exist. Word counts might be low, PDF records missing, or traces incomplete. Consider review before assessment submission.")
        else:
            lines.append("> [!TIP]")
            lines.append("> All systems checks pass cleanly. The generated book and tracing logs are ready for assessment delivery.")

        return "\n".join(lines)

    def generate_evaluation_report(self, request: EvaluationReportRequest) -> EvaluationReportResponse:
        self._check_book_exists(request.book_id)

        checks = []
        if request.include_chapter_checks:
            checks.extend(self._check_chapters(request.book_id))
        if request.include_export_checks:
            checks.extend(self._check_exports(request.book_id, request.run_id))
        if request.include_trace_checks:
            checks.extend(self._check_traces(request.book_id, request.run_id))
        if request.include_memory_checks:
            checks.extend(self._check_memory(request.book_id))

        total_checks = len(checks)
        pass_count = sum(1 for c in checks if c.status == "pass")
        warning_count = sum(1 for c in checks if c.status == "warning")
        fail_count = sum(1 for c in checks if c.status == "fail")
        skipped_count = sum(1 for c in checks if c.status == "skipped")

        overall_status = "pass"
        if fail_count > 0:
            overall_status = "fail"
        elif warning_count > 0:
            overall_status = "warning"

        markdown_report = self._build_markdown_report(request.book_id, request.run_id, checks)

        persisted_eval_ids = []
        if request.persist_eval_results:
            for c in checks:
                status_map = {
                    "pass": "passed",
                    "fail": "failed",
                    "warning": "warning",
                    "skipped": "skipped",
                }
                db_status = status_map.get(c.status, "skipped")

                payload = EvalResultCreate(
                    book_id=request.book_id,
                    run_id=request.run_id,
                    eval_name=c.check_name,
                    score=c.score,
                    status=db_status,
                    details=c.details or {},
                )
                eval_row = self.eval_service.create_eval_result(payload, book_id=request.book_id, run_id=request.run_id)
                persisted_eval_ids.append(eval_row.id)

        return EvaluationReportResponse(
            book_id=request.book_id,
            run_id=request.run_id,
            status=overall_status,
            total_checks=total_checks,
            pass_count=pass_count,
            warning_count=warning_count,
            fail_count=fail_count,
            skipped_count=skipped_count,
            checks=checks,
            markdown_report=markdown_report,
            persisted_eval_ids=persisted_eval_ids,
            metadata=request.metadata,
        )
