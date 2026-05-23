"""
AIuthor Backend Tests — Workflow Execution Service (Module 7.1A).

Tests that:
1. WorkflowExecutionService.list_workflows() returns all registered workflows.
2. WorkflowExecutionService.get_workflow_info() returns correct metadata.
3. WorkflowExecutionService.get_workflow_info() raises on unknown workflow.
4. WorkflowExecutionService.run_workflow_mock() executes all 5 nodes offline.
5. Mock execution returns 5 steps, correct status, and non-empty final_content.
6. run_workflow_real_dev exists and has correct signature (not called in tests).
7. All execution is completely offline — no external LLM calls.
"""
from __future__ import annotations

import inspect
import pytest
from sqlalchemy.orm import Session

from app.services.workflow_execution_service import WorkflowExecutionService
from app.workflows.schemas import WorkflowInput, WorkflowOutput, WorkflowInfo
from app.workflows.exceptions import WorkflowExecutionError


class TestWorkflowExecutionServiceMetadata:
    def test_list_workflows_returns_at_least_one(self, db: Session):
        """list_workflows must return at least one registered workflow."""
        svc = WorkflowExecutionService(db=db)
        workflows = svc.list_workflows()
        assert len(workflows) >= 1

    def test_list_workflows_contains_mini_book_pipeline(self, db: Session):
        """list_workflows must include mini_book_pipeline."""
        svc = WorkflowExecutionService(db=db)
        names = [w.workflow_name for w in svc.list_workflows()]
        assert "mini_book_pipeline" in names

    def test_list_workflows_returns_workflow_info(self, db: Session):
        """list_workflows entries are WorkflowInfo instances with correct fields."""
        svc = WorkflowExecutionService(db=db)
        workflows = svc.list_workflows()
        for wf in workflows:
            assert isinstance(wf, WorkflowInfo)
            assert wf.workflow_name
            assert wf.display_name
            assert isinstance(wf.nodes, list)

    def test_get_workflow_info_mini_book(self, db: Session):
        """get_workflow_info returns correct metadata for mini_book_pipeline."""
        svc = WorkflowExecutionService(db=db)
        info = svc.get_workflow_info("mini_book_pipeline")
        assert isinstance(info, WorkflowInfo)
        assert info.workflow_name == "mini_book_pipeline"
        assert info.supports_mock is True
        assert info.supports_real_dev is True
        expected_nodes = {"planner", "researcher", "writer", "editor", "fact_checker"}
        assert expected_nodes == set(info.nodes)

    def test_get_workflow_info_unknown_raises(self, db: Session):
        """get_workflow_info raises WorkflowExecutionError for unknown workflow."""
        svc = WorkflowExecutionService(db=db)
        with pytest.raises(WorkflowExecutionError) as exc_info:
            svc.get_workflow_info("nonexistent_workflow_xyz")
        assert "not registered" in str(exc_info.value).lower()


class TestWorkflowExecutionServiceMockRun:
    def test_mock_run_returns_workflow_output(self, db: Session):
        """run_workflow_mock returns a WorkflowOutput Pydantic instance."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Introduction to Python data structures")
        output = svc.run_workflow_mock(inp)
        assert isinstance(output, WorkflowOutput)

    def test_mock_run_status_completed(self, db: Session):
        """run_workflow_mock returns status='completed' on successful execution."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Blockchain fundamentals")
        output = svc.run_workflow_mock(inp)
        assert output.status == "completed"

    def test_mock_run_has_five_steps(self, db: Session):
        """run_workflow_mock executes all 5 pipeline nodes and records them."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="History of artificial intelligence")
        output = svc.run_workflow_mock(inp)
        assert len(output.steps) == 5

    def test_mock_run_step_names(self, db: Session):
        """Steps contain all 5 expected agent names in order."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Climate change science")
        output = svc.run_workflow_mock(inp)
        names = [s.agent_name for s in output.steps]
        expected = ["planner", "researcher", "writer", "editor", "fact_checker"]
        assert names == expected

    def test_mock_run_all_steps_completed(self, db: Session):
        """All 5 steps have status='completed' in mock mode."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Quantum computing basics")
        output = svc.run_workflow_mock(inp)
        for step in output.steps:
            assert step.status == "completed", f"Step '{step.agent_name}' has status '{step.status}'"

    def test_mock_run_final_content_not_empty(self, db: Session):
        """final_content must be a non-empty string after mock execution."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Space exploration milestones")
        output = svc.run_workflow_mock(inp)
        assert output.final_content is not None
        assert len(output.final_content) > 0

    def test_mock_run_metadata_has_execution_mode(self, db: Session):
        """Output metadata includes execution_mode='mock'."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Electric vehicles technology")
        output = svc.run_workflow_mock(inp)
        assert output.metadata is not None
        assert output.metadata.get("execution_mode") == "mock"

    def test_mock_run_uses_configured_workflow_name(self, db: Session):
        """WorkflowOutput.workflow_name matches the input workflow_name."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Renewable energy", workflow_name="mini_book_pipeline")
        output = svc.run_workflow_mock(inp)
        assert output.workflow_name == "mini_book_pipeline"

    def test_mock_run_with_full_context(self, db: Session):
        """run_workflow_mock handles full context_pack, memory_context, and metadata."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(
            topic="Machine learning in healthcare",
            genre="technical",
            reader_profile="data scientists",
            tone="precise",
            context_pack={"context_text": "Healthcare ML papers summary", "citations": ["ref1", "ref2"]},
            memory_context={"past_chapters": ["intro"]},
            metadata={"user_id": "user-001", "session": "abc"},
        )
        output = svc.run_workflow_mock(inp)
        assert output.status == "completed"
        assert len(output.steps) == 5

    def test_mock_run_does_not_call_external_llm(self, db: Session, monkeypatch):
        """run_workflow_mock must not invoke any external LLM API."""
        call_count = {"count": 0}

        original_run_mock = WorkflowExecutionService.run_workflow_mock

        def tracking_run_mock(self, input):
            # Patch the underlying AgentExecutionService.run_agent_once to fail if called
            from app.services.agent_execution_service import AgentExecutionService
            original_run_agent_once = AgentExecutionService.run_agent_once

            def boom_run_once(self, inp):
                call_count["count"] += 1
                raise RuntimeError("External LLM call intercepted — should not be called in mock mode")

            monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)
            result = original_run_mock(self, input)
            monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)
            return result

        monkeypatch.setattr(WorkflowExecutionService, "run_workflow_mock", tracking_run_mock)

        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Security in cloud computing")
        output = svc.run_workflow_mock(inp)
        assert output.status == "completed"
        assert call_count["count"] == 0, "run_agent_once (real LLM) was unexpectedly called"


class TestWorkflowExecutionServiceRealDev:
    def test_run_workflow_real_dev_method_exists(self, db: Session):
        """run_workflow_real_dev must exist and have correct signature."""
        svc = WorkflowExecutionService(db=db)
        assert hasattr(svc, "run_workflow_real_dev")
        sig = inspect.signature(svc.run_workflow_real_dev)
        assert "input" in sig.parameters

    def test_run_workflow_mock_method_exists(self, db: Session):
        """run_workflow_mock must exist and have correct signature."""
        svc = WorkflowExecutionService(db=db)
        assert hasattr(svc, "run_workflow_mock")
        sig = inspect.signature(svc.run_workflow_mock)
        assert "input" in sig.parameters
