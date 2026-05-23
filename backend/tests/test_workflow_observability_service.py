"""
AIuthor Backend Tests — Workflow Observability Service (Module 7.1B).
"""
from __future__ import annotations

import pytest
import uuid
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, AgentTrace, PromptLog, TokenCostLedger
from app.services.workflow_observability_service import WorkflowObservabilityService
from app.workflows.schemas import WorkflowTraceStep


@pytest.fixture
def test_project_and_run(db: Session) -> tuple[BookProject, BookRun]:
    """Helper fixture to create a valid BookProject and BookRun in DB."""
    proj = BookProject(
        topic="Testing Observability",
        reader_profile="developers",
        genre="technical",
        tone="precise",
        target_chapters=3,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)

    run = BookRun(
        book_id=proj.id,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return proj, run


class TestWorkflowObservabilityService:

    def test_persist_agent_step_trace_returns_workflow_trace_step(self, db: Session, test_project_and_run):
        """persist_agent_step_trace returns a populated WorkflowTraceStep schema."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="planner",
            agent_name="planner",
            execution_mode="mock",
            task="Write outline for testing",
            system_prompt="System instructions",
            user_prompt="User input task",
            output_content="Mocked planned outline content",
            structured_output={"chapters": []},
            status="completed",
            duration_ms=120,
            input_tokens=15,
            output_tokens=25,
            total_tokens=40,
            error_message=None,
            metadata={"user": "tester"},
        )

        assert isinstance(step, WorkflowTraceStep)
        assert step.step_name == "planner"
        assert step.status == "completed"
        assert step.trace_id is not None
        assert step.prompt_log_id is not None
        assert step.token_cost_id is not None
        assert step.duration_ms == 120
        assert step.content_preview == "Mocked planned outline content"
        assert step.metadata.get("user") == "tester"

    def test_persist_agent_step_trace_creates_agent_trace_row(self, db: Session, test_project_and_run):
        """persist_agent_step_trace successfully writes an AgentTrace row in DB."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="researcher",
            agent_name="researcher",
            execution_mode="mock",
            task="Find facts",
            system_prompt="System",
            user_prompt="User",
            output_content="Mock facts content",
            structured_output=None,
            status="completed",
            duration_ms=85,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            error_message=None,
        )

        db_trace = db.get(AgentTrace, step.trace_id)
        assert db_trace is not None
        assert db_trace.run_id == run.id
        assert db_trace.agent_name == "researcher"
        assert db_trace.status == "completed"
        assert db_trace.input_summary == "Find facts"
        assert db_trace.output_summary == "Mock facts content"

    def test_persist_agent_step_trace_creates_prompt_log_row(self, db: Session, test_project_and_run):
        """persist_agent_step_trace successfully writes a PromptLog row in DB."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="writer",
            agent_name="writer",
            execution_mode="mock",
            task="Write draft intro",
            system_prompt="System prompt block",
            user_prompt="User prompt block",
            output_content="Draft intro draft draft",
            structured_output=None,
            status="completed",
            duration_ms=450,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            error_message=None,
        )

        db_prompt = db.get(PromptLog, step.prompt_log_id)
        assert db_prompt is not None
        assert db_prompt.run_id == run.id
        assert db_prompt.agent_name == "writer"
        assert "System prompt block" in db_prompt.prompt_text
        assert "User prompt block" in db_prompt.prompt_text

    def test_persist_agent_step_trace_creates_token_cost_ledger_row(self, db: Session, test_project_and_run):
        """persist_agent_step_trace successfully writes a TokenCostLedger row in DB."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="editor",
            agent_name="editor",
            execution_mode="mock",
            task="Edit intro",
            system_prompt=None,
            user_prompt=None,
            output_content="Edited draft",
            structured_output=None,
            status="completed",
            duration_ms=180,
            input_tokens=100,
            output_tokens=150,
            total_tokens=250,
            error_message=None,
        )

        db_cost = db.get(TokenCostLedger, step.token_cost_id)
        assert db_cost is not None
        assert db_cost.run_id == run.id
        assert db_cost.agent_name == "editor"
        assert db_cost.input_tokens == 100
        assert db_cost.output_tokens == 150
        assert db_cost.total_tokens == 250

    def test_persist_agent_step_trace_handles_missing_token_counts(self, db: Session, test_project_and_run):
        """No TokenCostLedger is created if all token counts are None."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="fact_checker",
            agent_name="fact_checker",
            execution_mode="mock",
            task="Verify citations",
            system_prompt=None,
            user_prompt=None,
            output_content="Checked output",
            structured_output=None,
            status="completed",
            duration_ms=90,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            error_message=None,
        )

        assert step.token_cost_id is None

    def test_persist_agent_step_trace_handles_missing_prompts(self, db: Session, test_project_and_run):
        """No PromptLog is created if prompts are empty or None."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="fact_checker",
            agent_name="fact_checker",
            execution_mode="mock",
            task="Verify citations",
            system_prompt=None,
            user_prompt="",
            output_content="Checked output",
            structured_output=None,
            status="completed",
            duration_ms=90,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            error_message=None,
        )

        assert step.prompt_log_id is None

    def test_get_workflow_trace_bundle_returns_bundle(self, db: Session, test_project_and_run):
        """get_workflow_trace_bundle retrieves a dictionary containing lists of traces, prompts, etc."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        # Write some traces
        svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="planner",
            agent_name="planner",
            execution_mode="mock",
            task="Write outline",
            system_prompt="System outline",
            user_prompt="User outline",
            output_content="Content outline",
            structured_output=None,
            status="completed",
            duration_ms=100,
            input_tokens=10,
            output_tokens=10,
            total_tokens=20,
            error_message=None,
        )

        bundle = svc.get_workflow_trace_bundle(run.id)
        assert isinstance(bundle, dict)
        assert bundle["run_id"] == run.id
        assert len(bundle["traces"]) == 1
        assert len(bundle["prompt_logs"]) == 1
        assert len(bundle["token_cost_ledger"]) == 1

    def test_persistence_failure_rolls_back_and_returns_error_metadata(self, db: Session, test_project_and_run, monkeypatch):
        """DB failures during trace writes are caught, rolled back, and marked in step metadata."""
        proj, run = test_project_and_run
        svc = WorkflowObservabilityService(db)

        # Force a database exception during create_agent_trace
        from app.services.observability_service import ObservabilityService
        def fail_create_agent_trace(*args, **kwargs):
            raise RuntimeError("Database connection interrupted")
        monkeypatch.setattr(ObservabilityService, "create_agent_trace", fail_create_agent_trace)

        step = svc.persist_agent_step_trace(
            run_id=run.id,
            book_id=proj.id,
            chapter_id=None,
            workflow_name="mini_book_pipeline",
            step_name="planner",
            agent_name="planner",
            execution_mode="mock",
            task="Write outline",
            system_prompt="System",
            user_prompt="User",
            output_content="Content",
            structured_output=None,
            status="completed",
            duration_ms=100,
            input_tokens=10,
            output_tokens=10,
            total_tokens=20,
            error_message=None,
        )

        assert step.trace_id is None
        assert step.prompt_log_id is None
        assert step.token_cost_id is None
        assert "Database connection interrupted" in step.metadata["observability_error"]
