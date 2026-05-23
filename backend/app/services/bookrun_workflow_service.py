"""
AIuthor Backend — BookRun Workflow Service (Module 8.0).

Coordinates dynamic execution of multi-agent LangGraph workflows mapped directly
to database entities: BookProject, BookRun, and Chapter, including dynamic context packing.
"""
from __future__ import annotations

import logging
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, Chapter
from app.schemas.rag import ContextPackRequest
from app.workflows.schemas import (
    BookRunWorkflowRequest,
    BookRunWorkflowResponse,
    WorkflowInput,
    WorkflowTraceRequest,
)
from app.workflows.exceptions import WorkflowExecutionError, WorkflowConfigurationError
from app.services.exceptions import NotFoundError, ValidationServiceError
from app.services.book_service import BookProjectService
from app.services.run_service import BookRunService
from app.services.chapter_service import ChapterService
from app.services.context_pack_service import ContextPackService
from app.services.workflow_execution_service import WorkflowExecutionService
from app.services.workflow_observability_service import WorkflowObservabilityService

logger = logging.getLogger(__name__)


class BookRunWorkflowService:
    """
    Service layer integrating BookRun and BookProject with multi-agent workflows.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.book_service = BookProjectService(db)
        self.run_service = BookRunService(db)
        self.chapter_service = ChapterService(db)
        self.context_pack_service = ContextPackService(db)
        self.workflow_service = WorkflowExecutionService(db)
        self.observability_service = WorkflowObservabilityService(db)

    # ── Private helper operations ─────────────────────────────────────────────

    def _get_book(self, book_id: UUID) -> BookProject:
        """
        Validate BookProject exists and return it.
        Raises NotFoundError if missing.
        """
        book = self.db.get(BookProject, book_id)
        if book is None:
            raise NotFoundError(
                message="Book project not found",
                code="book_not_found",
                details={"book_id": str(book_id)},
            )
        return book

    def _get_or_create_run(
        self,
        book: BookProject,
        run_id: UUID | None = None,
        workflow_name: str = "full_agent_pipeline",
    ) -> BookRun:
        """
        If run_id provided, fetch and verify it belongs to the book.
        If not provided, dynamically create a new BookRun.
        """
        if run_id is not None:
            run = self.db.get(BookRun, run_id)
            if run is None:
                raise NotFoundError(
                    message="Book run not found",
                    code="run_not_found",
                    details={"run_id": str(run_id)},
                )
            if run.book_id != book.id:
                raise NotFoundError(
                    message="Book run does not belong to the specified book project",
                    code="run_book_mismatch",
                    details={"run_id": str(run_id), "book_id": str(book.id)},
                )
            return run
        else:
            from app.schemas.run import BookRunCreate
            run_payload = BookRunCreate(
                book_id=book.id,
                run_metadata={
                    "workflow_name": workflow_name,
                    "created_automatically": True,
                },
            )
            return self.run_service.create_run(run_payload)

    def _get_chapter_if_provided(self, book_id: UUID, chapter_id: UUID | None) -> Chapter | None:
        """
        If chapter_id provided, fetch and verify it belongs to the specified book.
        Raises NotFoundError if not found.
        """
        if chapter_id is None:
            return None
        return self.chapter_service.get_chapter(book_id, chapter_id)

    def _build_context_pack_if_requested(
        self,
        request: BookRunWorkflowRequest,
        book: BookProject,
        chapter: Chapter | None,
    ) -> dict | None:
        """
        If build_context_pack is requested, build a RAG context pack.
        Handles missing chunk environments gracefully without failing.
        """
        if not request.build_context_pack:
            return None

        # Build query: request.context_query or fallback to topic (+ chapter title if available)
        query = request.context_query
        if not query or not query.strip():
            query = book.topic
            if chapter and chapter.title:
                query = f"{book.topic} {chapter.title}"

        context_req = ContextPackRequest(
            query=query,
            book_id=book.id,
            chapter_id=chapter.id if chapter else None,
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
                context_dict["metadata"]["note"] = "No context chunks found. Workflow ran without RAG context."
            return context_dict

        except Exception as exc:
            logger.warning("Context pack construction skipped or fallback triggered: %s", exc)
            return {
                "query": query,
                "book_id": str(book.id),
                "chapter_id": str(chapter.id) if chapter else None,
                "context_text": "",
                "chunks": [],
                "citations": [],
                "total_chunks": 0,
                "total_context_chars": 0,
                "retrieval_mode": "hybrid_context_pack",
                "metadata": {
                    "note": "No context chunks found. Workflow ran without RAG context.",
                    "error": str(exc),
                },
            }

    def _build_workflow_input(
        self,
        request: BookRunWorkflowRequest,
        book: BookProject,
        run: BookRun,
        chapter: Chapter | None,
        context_pack: dict | None,
    ) -> WorkflowInput | WorkflowTraceRequest:
        """
        Synthesize workflow schema input models out of database entities.
        """
        # Map tone
        tone_val = book.tone if book.tone else None

        # Merge custom payload options
        payload = dict(request.payload) if request.payload else {}
        payload.update({
            "book_topic": book.topic,
            "book_genre": book.genre,
            "book_reader_profile": book.reader_profile,
            "book_tone": book.tone,
            "run_id": str(run.id),
        })
        if chapter:
            payload.update({
                "chapter_title": chapter.title,
                "chapter_number": chapter.chapter_number,
                "chapter_summary": chapter.summary,
            })

        # Merge metadata
        metadata = dict(request.metadata) if request.metadata else {}
        metadata.update({
            "execution_mode": request.execution_mode,
            "workflow_name": request.workflow_name,
            "book_id": str(book.id),
            "run_id": str(run.id),
        })
        if chapter:
            metadata["chapter_id"] = str(chapter.id)

        if request.traced:
            return WorkflowTraceRequest(
                workflow_name=request.workflow_name,
                run_id=run.id,
                book_id=book.id,
                chapter_id=chapter.id if chapter else None,
                topic=book.topic,
                genre=book.genre,
                reader_profile=book.reader_profile,
                tone=tone_val,
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
                chapter_id=chapter.id if chapter else None,
                topic=book.topic,
                genre=book.genre,
                reader_profile=book.reader_profile,
                tone=tone_val,
                context_pack=context_pack,
                payload=payload,
                metadata=metadata,
            )

    # ── Public execution interface ───────────────────────────────────────────

    def run_book_workflow(self, request: BookRunWorkflowRequest) -> BookRunWorkflowResponse:
        """
        Securely coordinate dynamic multi-agent workflows against DB book runs.
        """
        # 1. Validate Book
        book = self._get_book(request.book_id)

        # 2. Get or create BookRun
        run = self._get_or_create_run(book, request.run_id, request.workflow_name)

        # 3. Resolve optional Chapter
        chapter = self._get_chapter_if_provided(book.id, request.chapter_id)

        # 4. Mark run as running in the DB
        run = self.run_service.mark_run_started(run.id, current_agent="workflow_start")

        # 5. Compile context pack
        context_pack = self._build_context_pack_if_requested(request, book, chapter)

        # 6. Execute LangGraph compiled workflow
        try:
            wf_input = self._build_workflow_input(request, book, run, chapter, context_pack)

            if request.execution_mode == "mock":
                if request.traced:
                    wf_output = self.workflow_service.run_workflow_mock_traced(wf_input)
                else:
                    wf_output = self.workflow_service.run_workflow_mock(wf_input)
            else:
                # real_dev execution mode
                if request.traced:
                    wf_output = self.workflow_service.run_workflow_real_dev_traced(wf_input)
                else:
                    wf_output = self.workflow_service.run_workflow_real_dev(wf_input)

            # 7. Mark run completed
            self.run_service.mark_run_completed(run.id)
            run.current_agent = "completed"
            
            # If metadata has progress_percentage or status trace, we update them
            meta = dict(run.run_metadata) if run.run_metadata else {}
            meta["progress_percentage"] = 100.0
            meta["execution_mode"] = request.execution_mode
            run.run_metadata = meta
            self.db.commit()

            # Retrieve trace bundle if request was traced
            trace_bundle = None
            if request.traced and request.persist_traces:
                try:
                    trace_bundle = self.observability_service.get_workflow_trace_bundle(run.id)
                except Exception as trace_exc:
                    logger.warning("Trace bundle retrieval failed: %s", trace_exc)

            return BookRunWorkflowResponse(
                book_id=book.id,
                run_id=run.id,
                chapter_id=chapter.id if chapter else None,
                workflow_name=request.workflow_name,
                execution_mode=request.execution_mode,
                traced=request.traced,
                status="completed",
                workflow_output=wf_output.model_dump(),
                context_pack=context_pack,
                trace_bundle=trace_bundle,
                metadata=request.metadata,
            )

        except Exception as exc:
            # 8. Mark run failed
            logger.exception("BookRun workflow execution failed")
            error_msg = str(exc)
            self.run_service.mark_run_failed(run.id, error_message=error_msg)
            raise
