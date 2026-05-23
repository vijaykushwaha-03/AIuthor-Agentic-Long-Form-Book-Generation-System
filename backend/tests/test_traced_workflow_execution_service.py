"""
AIuthor Backend Tests — Traced Workflow Execution Service (Module 7.1B).
"""
from __future__ import annotations

import inspect
import pytest
import uuid
from sqlalchemy.orm import Session

from app.models import BookProject, BookRun, AgentTrace, PromptLog, TokenCostLedger
from app.services.workflow_execution_service import WorkflowExecutionService
from app.workflows.schemas import WorkflowTraceRequest, WorkflowTraceResponse


class TestTracedWorkflowExecutionService:

    def test_run_workflow_mock_traced_returns_response(self, db: Session):
        """run_workflow_mock_traced returns a WorkflowTraceResponse instance."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="Introduction to Advanced Agentic Coding",
            persist_traces=True,
        )
        resp = svc.run_workflow_mock_traced(req)
        assert isinstance(resp, WorkflowTraceResponse)

    def test_traced_mock_run_includes_five_steps(self, db: Session):
        """traced mock run executes all 5 sequential steps in order."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="Observability in Multi-Agent Systems",
            persist_traces=True,
        )
        resp = svc.run_workflow_mock_traced(req)
        assert len(resp.steps) == 5
        agent_names = [s.agent_name for s in resp.steps]
        assert agent_names == ["planner", "researcher", "writer", "editor", "fact_checker"]

    def test_traced_mock_run_has_execution_mode_mock(self, db: Session):
        """WorkflowTraceResponse execution_mode is mock."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="Sleek CSS frameworks",
            persist_traces=True,
        )
        resp = svc.run_workflow_mock_traced(req)
        assert resp.execution_mode == "mock"

    def test_traced_mock_run_persists_agent_traces(self, db: Session):
        """Traces are written to the agent_traces table when persist_traces=True."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="PostgreSQL pgvector native types",
            persist_traces=True,
        )
        resp = svc.run_workflow_mock_traced(req)
        
        # Verify run_id exists in AgentTrace
        assert resp.run_id is not None
        db_traces = db.query(AgentTrace).filter(AgentTrace.run_id == resp.run_id).all()
        assert len(db_traces) == 5
        for t in db_traces:
            assert t.status == "completed"

    def test_traced_mock_run_persists_prompt_logs(self, db: Session):
        """Prompts are written to the prompt_logs table when persist_traces=True."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="FastAPI Starlette routers order",
            persist_traces=True,
        )
        resp = svc.run_workflow_mock_traced(req)

        db_prompts = db.query(PromptLog).filter(PromptLog.run_id == resp.run_id).all()
        assert len(db_prompts) == 5
        for p in db_prompts:
            assert p.agent_name in ["planner", "researcher", "writer", "editor", "fact_checker"]
            assert len(p.prompt_text) > 0

    def test_traced_mock_run_does_not_call_real_llm(self, db: Session, monkeypatch):
        """run_workflow_mock_traced runs completely offline without real LLM calls."""
        call_count = {"count": 0}

        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, inp):
            call_count["count"] += 1
            raise RuntimeError("Intercepted real LLM execution inside mock test")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="SQLite JSON fallbacks",
            persist_traces=True,
        )
        resp = svc.run_workflow_mock_traced(req)
        
        assert resp.status == "completed"
        assert call_count["count"] == 0, "run_agent_once was called when mock was requested"
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)

    def test_traced_mock_run_with_persist_false_does_not_persist(self, db: Session):
        """No DB entries are written if persist_traces is set to False."""
        # Clean existing DB counts for comparison
        pre_traces = db.query(AgentTrace).count()
        pre_prompts = db.query(PromptLog).count()

        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(
            topic="Offline non-persistent testing",
            persist_traces=False,
        )
        resp = svc.run_workflow_mock_traced(req)

        assert resp.status == "completed"
        post_traces = db.query(AgentTrace).count()
        post_prompts = db.query(PromptLog).count()

        assert pre_traces == post_traces
        assert pre_prompts == post_prompts

        # Steps should still be returned, but IDs should be None
        for step in resp.steps:
            assert step.trace_id is None
            assert step.prompt_log_id is None

    def test_run_workflow_real_dev_traced_signature(self, db: Session):
        """run_workflow_real_dev_traced exists with correct signature but is not executed."""
        svc = WorkflowExecutionService(db=db)
        assert hasattr(svc, "run_workflow_real_dev_traced")
        sig = inspect.signature(svc.run_workflow_real_dev_traced)
        assert "input" in sig.parameters
