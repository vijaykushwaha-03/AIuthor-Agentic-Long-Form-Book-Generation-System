"""
AIuthor Backend — Chapter Generation Loop Service (Module 8.1).
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter
from app.schemas.rag import ContextPackRequest
from app.workflows.schemas import (
    ChapterGenerationRequest,
    ChapterGenerationItem,
    ChapterGenerationResponse,
    WorkflowInput,
    WorkflowTraceRequest,
)
from app.schemas.enums import ChapterStatus
from app.workflows.exceptions import WorkflowExecutionError
from app.services.exceptions import NotFoundError, ValidationServiceError
from app.services.book_service import BookProjectService
from app.services.run_service import BookRunService
from app.services.chapter_service import ChapterService
from app.services.context_pack_service import ContextPackService
from app.services.workflow_execution_service import WorkflowExecutionService
from app.services.workflow_observability_service import WorkflowObservabilityService

logger = logging.getLogger(__name__)


class ChapterGenerationService:
    """
    Coordinates sequential chapter-level book generation execution loops.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.book_service = BookProjectService(db)
        self.run_service = BookRunService(db)
        self.chapter_service = ChapterService(db)
        self.context_pack_service = ContextPackService(db)
        self.workflow_service = WorkflowExecutionService(db)
        self.workflow_observability_service = WorkflowObservabilityService(db)

    def _get_book(self, book_id: UUID) -> BookProject:
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _get_or_create_run(self, book: BookProject, run_id: UUID | None = None) -> BookRun:
        if run_id is not None:
            run = self.db.get(BookRun, run_id)
            if run is None:
                raise NotFoundError(
                    message="Book run not found",
                    code="run_not_found",
                    details={"run_id": str(run_id)},
                )
            if run.book_id != book.id:
                raise ValidationServiceError(
                    message="Book run does not belong to the specified book project",
                    code="run_book_mismatch",
                )
            return run
        else:
            from app.schemas.run import BookRunCreate
            run_payload = BookRunCreate(
                book_id=book.id,
                run_metadata={
                    "workflow_name": "full_agent_pipeline",
                    "module": "8.1",
                    "mode": "chapter_generation",
                    "created_automatically": True,
                },
            )
            return self.run_service.create_run(run_payload)

    def _select_chapters(self, request: ChapterGenerationRequest) -> list[Chapter]:
        if request.chapter_ids is not None:
            chapters = []
            for cid in request.chapter_ids:
                ch = self.db.get(Chapter, cid)
                if ch is None:
                    raise NotFoundError(
                        message=f"Chapter {cid} not found",
                        code="chapter_not_found",
                        details={"chapter_id": str(cid)},
                    )
                if ch.book_id != request.book_id:
                    raise ValidationServiceError(
                        message=f"Chapter {cid} does not belong to book project {request.book_id}",
                        code="chapter_book_mismatch",
                    )
                chapters.append(ch)
            chapters.sort(key=lambda c: c.chapter_number)
            return chapters

        elif request.chapter_numbers is not None:
            chapters = (
                self.db.query(Chapter)
                .filter(
                    Chapter.book_id == request.book_id,
                    Chapter.chapter_number.in_(request.chapter_numbers),
                )
                .order_by(Chapter.chapter_number)
                .all()
            )
            matched_numbers = {c.chapter_number for c in chapters}
            for num in request.chapter_numbers:
                if num not in matched_numbers:
                    raise ValidationServiceError(
                        message=f"Chapter number {num} not found in book project {request.book_id}",
                        code="chapter_number_not_found",
                    )
            return chapters

        else:
            chapters = (
                self.db.query(Chapter)
                .filter(Chapter.book_id == request.book_id)
                .order_by(Chapter.chapter_number)
                .all()
            )
            if not chapters:
                raise ValidationServiceError(
                    message=f"No chapters found for book project {request.book_id}",
                    code="no_chapters_found",
                )
            return chapters

    def _chapter_has_existing_content(self, chapter: Chapter) -> bool:
        return bool(
            (chapter.draft_text and chapter.draft_text.strip()) or
            (chapter.humanized_text and chapter.humanized_text.strip()) or
            (chapter.edited_text and chapter.edited_text.strip()) or
            (chapter.final_text and chapter.final_text.strip())
        )

    def _mark_chapter_running(self, chapter: Chapter) -> None:
        chapter.status = ChapterStatus.DRAFTING.value
        self.db.commit()

    def _mark_chapter_completed(
        self,
        chapter: Chapter,
        content: str,
        workflow_output: dict,
        context_pack: dict | None,
    ) -> None:
        if content:
            chapter.word_count = len(content.split())

        # Reset existing text fields
        chapter.draft_text = None
        chapter.humanized_text = None
        chapter.edited_text = None
        chapter.final_text = None

        # Map steps to corresponding fields
        steps = workflow_output.get("steps", [])
        for step in steps:
            agent = step.get("agent_name")
            step_content = step.get("content")
            if not step_content:
                continue
            if agent == "writer":
                chapter.draft_text = step_content
            elif agent == "humanizer":
                chapter.humanized_text = step_content
            elif agent == "editor":
                chapter.edited_text = step_content
            elif agent == "assembler":
                # The assembler node outputs a book-level outline summary package, not chapter-level prose.
                # We skip storing it in chapter.final_text to preserve the actual chapter prose.
                pass

        # Fallbacks for quality tiers: prefer editor > humanizer > writer > content
        if chapter.edited_text:
            chapter.final_text = chapter.edited_text
        elif chapter.humanized_text:
            chapter.final_text = chapter.humanized_text
        elif chapter.draft_text:
            chapter.final_text = chapter.draft_text

        if not chapter.final_text:
            chapter.final_text = content
        if not chapter.draft_text:
            chapter.draft_text = chapter.final_text

        # Record metadata inside chapter_contract JSON
        contract = dict(chapter.chapter_contract) if chapter.chapter_contract else {}
        contract.update({
            "workflow_name": workflow_output.get("workflow_name", "full_agent_pipeline"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "execution_mode": workflow_output.get("metadata", {}).get("execution_mode", "mock"),
            "content_source": "full_agent_pipeline",
            "context_pack_used": context_pack is not None,
            "traceable": workflow_output.get("metadata", {}).get("traced", True),
        })
        chapter.chapter_contract = contract
        chapter.status = ChapterStatus.COMPLETED.value
        self.db.commit()

    def _mark_chapter_failed(self, chapter: Chapter, error: Exception) -> None:
        chapter.status = ChapterStatus.FAILED.value
        contract = dict(chapter.chapter_contract) if chapter.chapter_contract else {}
        contract["error_message"] = str(error)
        chapter.chapter_contract = contract
        self.db.commit()

    def _build_chapter_context_pack(
        self,
        request: ChapterGenerationRequest,
        book: BookProject,
        chapter: Chapter,
    ) -> dict | None:
        if not request.build_context_pack:
            return None

        # Build context pack query
        if request.context_query_template:
            query = request.context_query_template
            btitle = book.topic or ""
            btopic = book.topic or ""
            cnum = str(chapter.chapter_number)
            ctitle = chapter.title or ""
            query = query.replace("{book_title}", btitle)
            query = query.replace("{book_topic}", btopic)
            query = query.replace("{chapter_number}", cnum)
            query = query.replace("{chapter_title}", ctitle)
        else:
            query = f"{book.topic} chapter {chapter.chapter_number}: {chapter.title}"

        context_req = ContextPackRequest(
            query=query,
            book_id=book.id,
            chapter_id=chapter.id,
            max_chunks=request.max_context_chunks,
            max_context_chars=request.max_context_chars,
            include_sources=True,
            include_memory_hints=False,
        )

        try:
            context_resp = self.context_pack_service.build_context_pack(context_req)
            import json
            context_dict = json.loads(context_resp.model_dump_json())
            if context_resp.total_chunks == 0:
                if "metadata" not in context_dict or context_dict["metadata"] is None:
                    context_dict["metadata"] = {}
                context_dict["metadata"]["note"] = "No context chunks found. Chapter generated without RAG context."
            return context_dict
        except Exception as exc:

            logger.warning("Context pack construction skipped or fallback triggered: %s", exc)
            return {
                "query": query,
                "book_id": str(book.id),
                "chapter_id": str(chapter.id),
                "context_text": "",
                "chunks": [],
                "citations": [],
                "total_chunks": 0,
                "total_context_chars": 0,
                "retrieval_mode": "hybrid_context_pack",
                "metadata": {
                    "note": "No context chunks found. Chapter generated without RAG context.",
                    "error": str(exc),
                },
            }

    def _build_workflow_trace_request(
        self,
        request: ChapterGenerationRequest,
        book: BookProject,
        run: BookRun,
        chapter: Chapter,
        context_pack: dict | None,
    ) -> WorkflowInput | WorkflowTraceRequest:
        payload = dict(request.payload) if request.payload else {}
        payload.update({
            "book_topic": book.topic,
            "book_genre": book.genre,
            "book_reader_profile": book.reader_profile,
            "book_tone": book.tone,
            "run_id": str(run.id),
            "chapter_id": str(chapter.id),
            "chapter_number": chapter.chapter_number,
            "chapter_title": chapter.title,
            "chapter_summary": chapter.summary,
        })

        metadata = dict(request.metadata) if request.metadata else {}
        metadata.update({
            "module": "8.1",
            "generation_scope": "chapter",
            "overwrite_existing": request.overwrite_existing,
            "execution_mode": request.execution_mode,
            "workflow_name": request.workflow_name,
            "book_id": str(book.id),
            "run_id": str(run.id),
            "chapter_id": str(chapter.id),
            "traced": request.traced,
        })

        if request.traced:
            return WorkflowTraceRequest(
                workflow_name=request.workflow_name,
                run_id=run.id,
                book_id=book.id,
                chapter_id=chapter.id,
                topic=book.topic,
                genre=book.genre,
                reader_profile=book.reader_profile,
                tone=book.tone,
                context_pack=context_pack,
                payload=payload,
                metadata=metadata,
                persist_traces=request.persist_traces,
            )
        else:
            return WorkflowInput(
                workflow_name=request.workflow_name,
                run_id=run.id,
                book_id=book.id,
                chapter_id=chapter.id,
                topic=book.topic,
                genre=book.genre,
                reader_profile=book.reader_profile,
                tone=book.tone,
                context_pack=context_pack,
                payload=payload,
                metadata=metadata,
            )

    def _extract_chapter_content(self, workflow_output: dict) -> str:
        steps = workflow_output.get("steps", [])
        for agent in ["editor", "humanizer", "writer"]:
            for step in steps:
                if step.get("agent_name") == agent and step.get("content"):
                    return step["content"]

        content = workflow_output.get("final_content")
        if content:
            if not (content.strip().startswith("{") or "outline" in content.lower()):
                return content

        raise ValidationServiceError(
            message="No text content generated in workflow output steps.",
            code="no_content_generated",
        )

    def generate_chapters(self, request: ChapterGenerationRequest) -> ChapterGenerationResponse:
        # 1. Validate Book
        book = self._get_book(request.book_id)

        # 2. Get or create BookRun
        run = self._get_or_create_run(book, request.run_id)

        # 3. Select target chapters
        selected_chapters = self._select_chapters(request)

        # 4. Limit chapters to max_chapters if supplied
        if request.max_chapters is not None:
            selected_chapters = selected_chapters[:request.max_chapters]

        # 5. Transition BookRun to running
        run = self.run_service.mark_run_started(run.id, current_agent="chapter_generation")

        total_requested = len(selected_chapters)
        completed_count = 0
        failed_count = 0
        skipped_count = 0
        chapters_result: list[ChapterGenerationItem] = []

        for ch in selected_chapters:
            # Check for existing content and overwrite rule
            if self._chapter_has_existing_content(ch) and not request.overwrite_existing:
                skipped_count += 1
                chapters_result.append(
                    ChapterGenerationItem(
                        chapter_id=ch.id,
                        chapter_number=ch.chapter_number,
                        title=ch.title,
                        status=ch.status,
                        workflow_status="skipped",
                        content_preview="Existing content preserved.",
                        content_chars=0,
                        metadata={"reason": "overwrite_existing_false"},
                    )
                )
                continue

            try:
                # Mark chapter running
                self._mark_chapter_running(ch)
                run.current_agent = f"generating_chapter_{ch.chapter_number}"
                self.db.commit()

                # Build context
                context_pack = self._build_chapter_context_pack(request, book, ch)

                # Assemble workflow input
                wf_input = self._build_workflow_trace_request(request, book, run, ch, context_pack)

                # Execute workflow
                if request.execution_mode == "mock":
                    if request.traced:
                        wf_output = self.workflow_service.run_workflow_mock_traced(wf_input)
                    else:
                        wf_output = self.workflow_service.run_workflow_mock(wf_input)
                else:
                    if request.traced:
                        wf_output = self.workflow_service.run_workflow_real_dev_traced(wf_input)
                    else:
                        wf_output = self.workflow_service.run_workflow_real_dev(wf_input)

                wf_dict = wf_output.model_dump()
                content = self._extract_chapter_content(wf_dict)

                # Persist content
                if request.persist_chapter_content:
                    self._mark_chapter_completed(ch, content, wf_dict, context_pack)

                completed_count += 1
                trace_count = len(wf_dict.get("steps", []))

                chapters_result.append(
                    ChapterGenerationItem(
                        chapter_id=ch.id,
                        chapter_number=ch.chapter_number,
                        title=ch.title,
                        status=ch.status,
                        workflow_status="completed",
                        content_preview=content[:200] if content else "",
                        content_chars=len(content) if content else 0,
                        trace_count=trace_count,
                        metadata=wf_dict.get("metadata"),
                    )
                )

            except Exception as exc:
                logger.exception("Failed generating chapter_number=%d", ch.chapter_number)
                self._mark_chapter_failed(ch, exc)
                failed_count += 1
                chapters_result.append(
                    ChapterGenerationItem(
                        chapter_id=ch.id,
                        chapter_number=ch.chapter_number,
                        title=ch.title,
                        status=ch.status,
                        workflow_status="failed",
                        error_message=str(exc),
                    )
                )

            # Update progress dynamically
            processed_count = completed_count + failed_count + skipped_count
            progress_percent = round((processed_count / total_requested) * 100, 2)
            meta = dict(run.run_metadata) if run.run_metadata else {}
            meta["progress_percentage"] = float(progress_percent)
            meta["processed_chapters"] = processed_count
            meta["total_chapters"] = total_requested
            run.run_metadata = meta
            self.db.commit()

        # Update run status
        if completed_count == 0 and total_requested > skipped_count:
            self.run_service.mark_run_failed(
                run.id,
                error_message="All targeted chapters failed to generate.",
            )
        else:
            self.run_service.mark_run_completed(run.id)
            run.current_agent = "completed"
            self.db.commit()

        trace_bundle = None
        if request.traced and request.persist_traces and completed_count > 0:
            try:
                trace_bundle = self.workflow_observability_service.get_workflow_trace_bundle(run.id)
            except Exception as trace_exc:
                logger.warning("Trace bundle retrieval failed: %s", trace_exc)

        return ChapterGenerationResponse(
            book_id=book.id,
            run_id=run.id,
            workflow_name=request.workflow_name,
            execution_mode=request.execution_mode,
            traced=request.traced,
            total_requested=total_requested,
            completed_count=completed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            chapters=chapters_result,
            status=run.status,
            trace_bundle=trace_bundle,
            metadata=request.metadata,
        )
