"""
AIuthor Backend Tests — Workflow Schemas and LangGraph Graph (Module 7.1A).

Tests that:
1. WorkflowInput Pydantic validation is correct.
2. WorkflowOutput can be constructed and serialized.
3. AIuthorWorkflowState TypedDict is compatible with LangGraph.
4. build_mini_book_workflow() compiles without error.
5. REGISTERED_WORKFLOWS contains mini_book_pipeline.
6. workflow_input_to_state produces a valid initial state.
7. state_to_workflow_output converts state to WorkflowOutput.
"""
from __future__ import annotations

import pytest
from uuid import uuid4

from app.workflows.schemas import WorkflowInput, WorkflowOutput, WorkflowStepOutput, WorkflowInfo
from app.workflows.exceptions import WorkflowError, WorkflowExecutionError
from app.workflows.state import AIuthorWorkflowState, workflow_input_to_state, state_to_workflow_output
from app.workflows.graph import build_mini_book_workflow, REGISTERED_WORKFLOWS


# ── WorkflowInput schema tests ────────────────────────────────────────────────

class TestWorkflowInputSchema:
    def test_minimal_valid_input(self):
        """WorkflowInput requires only topic."""
        inp = WorkflowInput(topic="Python programming best practices")
        assert inp.topic == "Python programming best practices"
        assert inp.workflow_name == "mini_book_pipeline"
        assert inp.genre is None
        assert inp.run_id is None

    def test_full_workflow_input(self):
        """WorkflowInput accepts all optional fields."""
        run_id = uuid4()
        inp = WorkflowInput(
            topic="AI in medicine",
            genre="non-fiction",
            reader_profile="medical professionals",
            tone="authoritative",
            run_id=run_id,
            context_pack={"key": "value"},
            memory_context={"past": "chapter 1"},
            metadata={"user_id": "test-user"},
        )
        assert inp.topic == "AI in medicine"
        assert inp.genre == "non-fiction"
        assert inp.run_id == run_id
        assert inp.context_pack == {"key": "value"}

    def test_topic_required(self):
        """WorkflowInput without topic must raise ValidationError."""
        with pytest.raises(Exception):
            WorkflowInput()  # topic is missing → pydantic error

    def test_empty_topic_fails(self):
        """WorkflowInput with empty string topic must fail validation."""
        with pytest.raises(Exception):
            WorkflowInput(topic="")


# ── WorkflowOutput schema tests ───────────────────────────────────────────────

class TestWorkflowOutputSchema:
    def test_minimal_valid_output(self):
        """WorkflowOutput can be built with workflow_name and status alone."""
        out = WorkflowOutput(workflow_name="mini_book_pipeline", status="completed")
        assert out.workflow_name == "mini_book_pipeline"
        assert out.status == "completed"
        assert out.steps == []
        assert out.final_content is None

    def test_output_with_steps(self):
        """WorkflowOutput correctly stores WorkflowStepOutput items."""
        step = WorkflowStepOutput(
            step_name="planner",
            agent_name="planner",
            status="completed",
            content="Chapter 1: Introduction",
        )
        out = WorkflowOutput(
            workflow_name="mini_book_pipeline",
            status="completed",
            steps=[step],
            final_content="Chapter 1: Introduction",
        )
        assert len(out.steps) == 1
        assert out.steps[0].step_name == "planner"
        assert out.final_content == "Chapter 1: Introduction"

    def test_json_serialization(self):
        """WorkflowOutput serializes to JSON without errors."""
        out = WorkflowOutput(
            workflow_name="mini_book_pipeline",
            status="completed",
            metadata={"key": "value"},
        )
        data = out.model_dump()
        assert data["workflow_name"] == "mini_book_pipeline"
        assert data["status"] == "completed"
        assert data["metadata"] == {"key": "value"}


# ── WorkflowInfo tests ────────────────────────────────────────────────────────

class TestWorkflowInfo:
    def test_workflow_info_fields(self):
        """WorkflowInfo captures expected metadata fields."""
        info = WorkflowInfo(
            workflow_name="mini_book_pipeline",
            display_name="Mini Book Pipeline",
            description="A 5-step sequential pipeline.",
            nodes=["planner", "researcher", "writer", "editor", "fact_checker"],
        )
        assert info.workflow_name == "mini_book_pipeline"
        assert "planner" in info.nodes
        assert info.supports_mock is True
        assert info.supports_real_dev is True
        assert info.enabled is True


# ── Exception class tests ─────────────────────────────────────────────────────

class TestWorkflowExceptions:
    def test_workflow_error_base(self):
        """WorkflowError captures message, workflow_name, and details."""
        exc = WorkflowError(message="test error", workflow_name="mini_book_pipeline")
        assert str(exc) == "test error"
        assert exc.workflow_name == "mini_book_pipeline"
        assert exc.details == {}

    def test_workflow_execution_error_is_workflow_error(self):
        """WorkflowExecutionError is a subclass of WorkflowError."""
        exc = WorkflowExecutionError(
            message="execution failed",
            workflow_name="mini_book_pipeline",
            details={"node": "planner"},
        )
        assert isinstance(exc, WorkflowError)
        assert exc.details == {"node": "planner"}


# ── State tests ───────────────────────────────────────────────────────────────

class TestWorkflowState:
    def test_workflow_input_to_state_fills_all_fields(self):
        """workflow_input_to_state correctly maps all WorkflowInput fields to state."""
        run_id = uuid4()
        inp = WorkflowInput(
            topic="Machine learning trends",
            genre="technical",
            reader_profile="engineers",
            tone="precise",
            run_id=run_id,
        )
        state = workflow_input_to_state(inp, execution_mode="mock")
        assert state["topic"] == "Machine learning trends"
        assert state["genre"] == "technical"
        assert state["reader_profile"] == "engineers"
        assert state["tone"] == "precise"
        assert state["run_id"] == str(run_id)
        assert state["execution_mode"] == "mock"
        assert state["status"] == "running"
        assert state["planner_output"] is None
        assert state["steps"] == []
        assert state["error_message"] is None

    def test_state_to_workflow_output_extracts_content(self):
        """state_to_workflow_output selects correct final content (fact_checker > writer)."""
        state: AIuthorWorkflowState = {
            "workflow_name": "mini_book_pipeline",
            "execution_mode": "mock",
            "run_id": None,
            "book_id": None,
            "chapter_id": None,
            "topic": "AI history",
            "genre": None,
            "reader_profile": None,
            "tone": None,
            "task": None,
            "context_pack": None,
            "memory_context": None,
            "payload": None,
            "metadata": {},
            "planner_output": {"content": "Chapter plan", "status": "completed", "agent_name": "planner"},
            "researcher_output": None,
            "writer_output": {"content": "Writer draft", "status": "completed", "agent_name": "writer"},
            "editor_output": None,
            "fact_checker_output": {"content": "Fact checked text", "status": "completed", "agent_name": "fact_checker"},
            "steps": [
                {
                    "step_name": "planner",
                    "agent_name": "planner",
                    "status": "completed",
                    "content": "Chapter plan",
                    "structured_output": None,
                    "error_message": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "metadata": {},
                }
            ],
            "status": "completed",
            "error_message": None,
        }
        output = state_to_workflow_output(state)
        assert output.workflow_name == "mini_book_pipeline"
        assert output.status == "completed"
        assert output.final_content == "Fact checked text"  # fact_checker takes priority
        assert len(output.steps) == 1

    def test_state_to_workflow_output_falls_back_to_writer(self):
        """state_to_workflow_output falls back to writer_output if fact_checker is absent."""
        state: AIuthorWorkflowState = {
            "workflow_name": "mini_book_pipeline",
            "execution_mode": "mock",
            "run_id": None,
            "book_id": None,
            "chapter_id": None,
            "topic": "quantum computing",
            "genre": None,
            "reader_profile": None,
            "tone": None,
            "task": None,
            "context_pack": None,
            "memory_context": None,
            "payload": None,
            "metadata": {},
            "planner_output": None,
            "researcher_output": None,
            "writer_output": {"content": "Writer content here", "status": "completed", "agent_name": "writer"},
            "editor_output": None,
            "fact_checker_output": None,
            "steps": [],
            "status": "completed",
            "error_message": None,
        }
        output = state_to_workflow_output(state)
        assert output.final_content == "Writer content here"


# ── LangGraph graph compilation tests ────────────────────────────────────────

class TestGraphCompilation:
    def test_mini_book_pipeline_registered(self):
        """REGISTERED_WORKFLOWS must contain mini_book_pipeline."""
        assert "mini_book_pipeline" in REGISTERED_WORKFLOWS
        info = REGISTERED_WORKFLOWS["mini_book_pipeline"]
        assert info.workflow_name == "mini_book_pipeline"
        assert len(info.nodes) == 5
        assert "planner" in info.nodes
        assert "fact_checker" in info.nodes

    def test_build_mini_book_workflow_compiles(self):
        """build_mini_book_workflow() must return a compiled graph without errors."""
        compiled = build_mini_book_workflow()
        assert compiled is not None

    def test_compiled_graph_is_invocable(self):
        """The compiled graph must have an invoke method."""
        compiled = build_mini_book_workflow()
        assert hasattr(compiled, "invoke")
