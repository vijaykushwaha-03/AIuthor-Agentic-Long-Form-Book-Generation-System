"""
AIuthor Backend — Workflow Execution Service (Module 7.2A).

Provides service-layer methods for running, mocking, and inspecting
LangGraph workflow pipelines dynamically based on selected workflow configurations.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.workflows.schemas import (
    WorkflowInput,
    WorkflowOutput,
    WorkflowInfo,
    WorkflowTraceRequest,
    WorkflowTraceStep,
    WorkflowTraceResponse,
)
from app.workflows.exceptions import WorkflowExecutionError, WorkflowConfigurationError
from app.workflows.state import workflow_input_to_state
from app.services.workflow_observability_service import WorkflowObservabilityService

logger = logging.getLogger(__name__)


class WorkflowExecutionService:
    """
    Service that coordinates mock and real-dev execution of LangGraph workflows
    supporting persistent run tracing, prompt logging, and token cost ledgering.
    """

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    # ── Metadata helpers ──────────────────────────────────────────────────────

    def list_workflows(self) -> list[WorkflowInfo]:
        """
        Return metadata for all registered LangGraph workflows.
        """
        from app.workflows.graph import REGISTERED_WORKFLOWS
        return list(REGISTERED_WORKFLOWS.values())

    def get_workflow_info(self, workflow_name: str) -> WorkflowInfo:
        """
        Return metadata for a single workflow by name.

        Raises:
            WorkflowExecutionError: If the workflow_name is not registered.
        """
        from app.workflows.graph import REGISTERED_WORKFLOWS
        if workflow_name not in REGISTERED_WORKFLOWS:
            raise WorkflowExecutionError(
                message=f"Workflow '{workflow_name}' is not registered.",
                workflow_name=workflow_name,
            )
        return REGISTERED_WORKFLOWS[workflow_name]


    def run_workflow_real_dev(self, input: WorkflowInput) -> WorkflowOutput:
        """
        Run the workflow using the configured real LLM provider (Gemini / OpenAI).

        IMPORTANT: This method calls external LLM APIs and incurs cost.
        It must only be called from the gated endpoint when ENABLE_REAL_WORKFLOW_TEST_API=true.
        Never call this from automated unit or integration tests.
        """
        logger.info(
            "WorkflowExecutionService.run_workflow_real_dev: %s — REAL LLM CALL",
            input.workflow_name,
        )
        from app.workflows.graph import run_registered_workflow
        return run_registered_workflow(input, execution_mode="real_dev")

    # ── Traced execution methods (Module 7.2A) ───────────────────────────────

    def run_workflow_real_dev_traced(self, input: WorkflowTraceRequest) -> WorkflowTraceResponse:

        """
        Run the workflow in real_dev mode and persist traces if enabled.
        """
        return self._run_workflow_traced(input, execution_mode="real_dev")

    def _run_workflow_traced(
        self,
        input: WorkflowTraceRequest,
        execution_mode: str,
    ) -> WorkflowTraceResponse:
        """
        Common execution wrapper that runs the graph and writes traces to the database.
        """
        workflow_name = input.workflow_name or "mini_book_pipeline"
        logger.info(
            "WorkflowExecutionService._run_workflow_traced: %s in %s mode",
            workflow_name,
            execution_mode,
        )

        run_id = input.run_id
        book_id = input.book_id

        # 1. Resolve and pre-populate DB elements if persistence is requested
        if input.persist_traces and self.db is not None:
            from app.models import BookProject, BookRun
            db_book = None
            if book_id is not None:
                db_book = self.db.get(BookProject, book_id)
            if db_book is None:
                db_book = self.db.query(BookProject).first()
                if not db_book:
                    db_book = BookProject(
                        topic=input.topic or "Traced Workflow Topic",
                        reader_profile=input.reader_profile or "General audience",
                        genre=input.genre or "General",
                        tone=input.tone or "Informative",
                        target_chapters=3,
                    )
                    self.db.add(db_book)
                    self.db.commit()
                    self.db.refresh(db_book)
                book_id = db_book.id

            if run_id is None:
                run_id = uuid.uuid4()

            db_run = self.db.get(BookRun, run_id)
            if db_run is None:
                db_run = BookRun(
                    id=run_id,
                    book_id=book_id,
                    status="running",
                    started_at=datetime.utcnow(),
                    run_metadata=input.metadata or {},
                )
                self.db.add(db_run)
                self.db.commit()
                self.db.refresh(db_run)
            else:
                db_run.status = "running"
                db_run.started_at = db_run.started_at or datetime.utcnow()
                self.db.commit()

        # Update input with resolved IDs
        input_copy = input.model_copy(update={"run_id": run_id, "book_id": book_id})

        # 2. Compile the correct sequential LangGraph pipeline based on workflow_name
        initial_state = workflow_input_to_state(input_copy, execution_mode=execution_mode)
        
        if workflow_name == "mini_book_pipeline":
            from app.workflows.graph import build_mini_book_workflow
            compiled_graph = build_mini_book_workflow()
        elif workflow_name == "full_agent_pipeline":
            from app.workflows.graph import build_full_agent_workflow
            compiled_graph = build_full_agent_workflow()
        else:
            raise WorkflowConfigurationError(
                message=f"Workflow '{workflow_name}' is not registered or supported.",
                workflow_name=workflow_name,
            )

        try:
            final_state = compiled_graph.invoke(initial_state)
            final_status = final_state.get("status", "completed")
            error_msg = final_state.get("error_message")
        except Exception as exc:
            final_status = "failed"
            error_msg = str(exc)
            final_state = initial_state

        # 3. Update DB BookRun status if persisting
        if input.persist_traces and self.db is not None and run_id is not None:
            from app.models import BookRun
            db_run = self.db.get(BookRun, run_id)
            if db_run:
                db_run.status = final_status
                db_run.completed_at = datetime.utcnow()
                if error_msg:
                    db_run.error_message = error_msg
                self.db.commit()

        # 4. Process and persist each step's trace
        traced_steps = []
        obs_service = WorkflowObservabilityService(self.db) if self.db is not None else None

        for step in final_state.get("trace_steps", []):
            if input.persist_traces and obs_service is not None:
                trace_step = obs_service.persist_agent_step_trace(
                    run_id=run_id,
                    book_id=book_id,
                    chapter_id=input.chapter_id,
                    workflow_name=workflow_name,
                    step_name=step["step_name"],
                    agent_name=step["agent_name"],
                    execution_mode=execution_mode,
                    task=step["task"],
                    system_prompt=step["system_prompt"],
                    user_prompt=step["user_prompt"],
                    output_content=step["content"],
                    structured_output=step["structured_output"],
                    status=step["status"],
                    duration_ms=step["duration_ms"],
                    input_tokens=step["input_tokens"],
                    output_tokens=step["output_tokens"],
                    total_tokens=step["total_tokens"],
                    error_message=step["error_message"],
                    metadata=step["metadata"],
                )
                traced_steps.append(trace_step)
            else:
                traced_steps.append(
                    WorkflowTraceStep(
                        step_name=step["step_name"],
                        agent_name=step["agent_name"],
                        status=step["status"],
                        trace_id=None,
                        prompt_log_id=None,
                        token_cost_id=None,
                        duration_ms=step["duration_ms"],
                        input_tokens=step["input_tokens"],
                        output_tokens=step["output_tokens"],
                        total_tokens=step["total_tokens"],
                        error_message=step["error_message"],
                        content_preview=step["content"][:1000] if step["content"] else None,
                        content=step["content"],
                        metadata=step["metadata"],
                    )
                )

        # 5. Extract compiled trace bundle
        trace_bundle = None
        if input.persist_traces and obs_service is not None and run_id is not None:
            try:
                trace_bundle = obs_service.get_workflow_trace_bundle(run_id)
            except Exception as bundle_exc:
                logger.error("Failed to compile trace bundle: %s", bundle_exc)

        # 6. Extract final content: prefer assembler > fact_checker > editor > writer > planner
        final_content = None
        for key in ("assembler_output", "fact_checker_output", "editor_output", "writer_output", "planner_output"):
            agent_out = final_state.get(key)
            if agent_out and agent_out.get("content"):
                final_content = agent_out["content"]
                break

        return WorkflowTraceResponse(
            workflow_name=workflow_name,
            status=final_status,
            run_id=run_id,
            book_id=book_id,
            chapter_id=input.chapter_id,
            execution_mode=execution_mode,
            final_content=final_content,
            steps=traced_steps,
            trace_bundle=trace_bundle,
            error_message=error_msg,
            metadata={
                **(final_state.get("metadata") or {}),
                "execution_mode": execution_mode,
                "topic": input.topic,
            },
        )
