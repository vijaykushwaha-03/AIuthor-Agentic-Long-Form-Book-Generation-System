"""
AIuthor Backend — Workflow Observability Service (Module 7.1B).

Manages database persistence of agent execution traces, prompt logs, and token ledger rows.
"""
from __future__ import annotations

import logging
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.schemas.observability import (
    AgentTraceCreate,
    PromptLogCreate,
    TokenCostLedgerCreate,
)
from app.workflows.schemas import WorkflowTraceStep
from app.services.observability_service import ObservabilityService

logger = logging.getLogger(__name__)


class WorkflowObservabilityService:
    """
    Service coordinating step-by-step trace and cost persistence for workflows.
    Ensures observability database updates are isolated and non-fatal.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.observability_service = ObservabilityService(db)

    def persist_agent_step_trace(
        self,
        *,
        run_id: UUID | None,
        book_id: UUID | None,
        chapter_id: UUID | None,
        workflow_name: str,
        step_name: str,
        agent_name: str,
        execution_mode: str,
        task: str,
        system_prompt: str | None,
        user_prompt: str | None,
        output_content: str | None,
        structured_output: dict | None,
        status: str,
        duration_ms: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
        error_message: str | None,
        metadata: dict | None = None,
    ) -> WorkflowTraceStep:
        """
        Persists trace, prompt, and token cost log rows for an agent execution step.
        Rolls back transactions on DB write errors and returns the step response with error tags.
        """
        trace_id = None
        prompt_log_id = None
        token_cost_id = None
        observability_error = None

        # Determine timestamps
        completed_at = datetime.utcnow()
        started_at = None
        if duration_ms is not None:
            started_at = completed_at - timedelta(milliseconds=duration_ms)

        # Only proceed with database writes if run_id is supplied
        if run_id is not None:
            try:
                # 1. Persist AgentTrace
                trace_payload = AgentTraceCreate(
                    run_id=run_id,
                    book_id=book_id,
                    agent_name=agent_name,
                    input_summary=task[:5000] if task else None,
                    output_summary=output_content[:5000] if output_content else None,
                    status=status,
                    error_message=error_message[:10000] if error_message else None,
                    started_at=started_at,
                    completed_at=completed_at,
                    trace_metadata={
                        "execution_mode": execution_mode,
                        "duration_ms": duration_ms,
                        "step_name": step_name,
                        **(metadata or {}),
                    },
                )
                trace_row = self.observability_service.create_agent_trace(trace_payload, run_id=run_id)
                trace_id = trace_row.id

                # 2. Persist PromptLog
                if system_prompt or user_prompt:
                    prompt_text = f"=== SYSTEM ===\n{system_prompt or ''}\n\n=== USER ===\n{user_prompt or ''}"
                    if len(prompt_text.strip()) >= 3:
                        prompt_payload = PromptLogCreate(
                            run_id=run_id,
                            book_id=book_id,
                            agent_name=agent_name,
                            model_name=metadata.get("model") if metadata else None,
                            prompt_name=f"{agent_name}_workflow_prompt",
                            prompt_text=prompt_text,
                            input_payload={"task": task},
                            output_payload={
                                "content": output_content,
                                "structured_output": structured_output,
                            },
                        )
                        prompt_row = self.observability_service.create_prompt_log(prompt_payload, run_id=run_id)
                        prompt_log_id = prompt_row.id

                # 3. Persist TokenCostLedger if counts are provided
                has_tokens = (input_tokens is not None) or (output_tokens is not None) or (total_tokens is not None)
                if has_tokens:
                    token_payload = TokenCostLedgerCreate(
                        run_id=run_id,
                        book_id=book_id,
                        agent_name=agent_name,
                        model_name=metadata.get("model") if (metadata and metadata.get("model")) else ("mock-model" if execution_mode == "mock" else "gemini-2.5-flash"),
                        input_tokens=input_tokens or 0,
                        output_tokens=output_tokens or 0,
                        total_tokens=total_tokens or ((input_tokens or 0) + (output_tokens or 0)),
                        ledger_metadata={"execution_mode": execution_mode},
                    )
                    token_row = self.observability_service.create_token_cost(token_payload, run_id=run_id)
                    token_cost_id = token_row.id

            except Exception as db_exc:
                logger.exception("Failed to write workflow step trace to database")
                self.db.rollback()
                observability_error = str(db_exc)

        # Assemble step metadata
        step_metadata = dict(metadata) if metadata else {}
        if observability_error:
            step_metadata["observability_error"] = observability_error

        return WorkflowTraceStep(
            step_name=step_name,
            agent_name=agent_name,
            status=status,
            trace_id=trace_id,
            prompt_log_id=prompt_log_id,
            token_cost_id=token_cost_id,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            error_message=error_message,
            content_preview=output_content[:1000] if output_content else None,
            metadata=step_metadata,
        )

    def get_workflow_trace_bundle(self, run_id: UUID) -> dict:
        """
        Retrieves the compiled execution trace bundle for a specific run ID.
        """
        bundle = self.observability_service.get_trace_bundle(run_id)
        return bundle.model_dump()
