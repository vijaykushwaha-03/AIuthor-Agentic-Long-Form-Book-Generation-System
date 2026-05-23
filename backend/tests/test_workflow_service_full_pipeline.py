"""
AIuthor Backend Tests — Workflow Service Multi-Workflow Execution (Module 7.2A).
"""
from __future__ import annotations

import inspect
import pytest
from sqlalchemy.orm import Session

from app.models import AgentTrace, PromptLog
from app.services.workflow_execution_service import WorkflowExecutionService
from app.workflows.schemas import WorkflowInput, WorkflowTraceRequest, WorkflowTraceResponse


class TestWorkflowServiceFullPipeline:

    def test_list_workflows_returns_both_pipelines(self, db: Session):
        """list_workflows returns both mini_book_pipeline and full_agent_pipeline."""
        svc = WorkflowExecutionService(db=db)
        names = [w.workflow_name for w in svc.list_workflows()]
        assert "mini_book_pipeline" in names
        assert "full_agent_pipeline" in names

    def test_get_workflow_info_full_agent_pipeline_returns_eight_nodes(self, db: Session):
        """get_workflow_info returns 8 nodes for full_agent_pipeline."""
        svc = WorkflowExecutionService(db=db)
        info = svc.get_workflow_info("full_agent_pipeline")
        assert len(info.nodes) == 8
        assert "humanizer" in info.nodes
        assert "memory_keeper" in info.nodes
        assert "assembler" in info.nodes

    def test_run_workflow_mock_defaults_to_mini_pipeline(self, db: Session):
        """run_workflow_mock defaults to mini_book_pipeline if workflow_name is omitted or empty."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Artificial intelligence history")
        output = svc.run_workflow_mock(inp)
        assert output.workflow_name == "mini_book_pipeline"
        assert len(output.steps) == 5

    def test_run_workflow_mock_with_full_agent_pipeline_returns_eight_steps(self, db: Session):
        """run_workflow_mock executes exactly 8 steps for full_agent_pipeline."""
        svc = WorkflowExecutionService(db=db)
        inp = WorkflowInput(topic="Serverless computing", workflow_name="full_agent_pipeline")
        output = svc.run_workflow_mock(inp)
        assert output.workflow_name == "full_agent_pipeline"
        assert len(output.steps) == 8

    def test_run_workflow_mock_traced_with_full_agent_pipeline_returns_eight_steps(self, db: Session):
        """run_workflow_mock_traced executes exactly 8 traced steps for full_agent_pipeline."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(topic="Distributed consensus", workflow_name="full_agent_pipeline", persist_traces=True)
        resp = svc.run_workflow_mock_traced(req)
        assert isinstance(resp, WorkflowTraceResponse)
        assert len(resp.steps) == 8

    def test_traced_full_workflow_persists_eight_agent_traces(self, db: Session):
        """Traced full pipeline writes 8 AgentTrace rows into DB when persist_traces=True."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(topic="Rust programming language", workflow_name="full_agent_pipeline", persist_traces=True)
        resp = svc.run_workflow_mock_traced(req)
        
        assert resp.run_id is not None
        db_traces = db.query(AgentTrace).filter(AgentTrace.run_id == resp.run_id).all()
        assert len(db_traces) == 8
        for trace in db_traces:
            assert trace.status == "completed"

    def test_traced_full_workflow_persists_eight_prompt_logs(self, db: Session):
        """Traced full pipeline writes 8 PromptLog rows into DB when persist_traces=True."""
        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(topic="Docker and Kubernetes", workflow_name="full_agent_pipeline", persist_traces=True)
        resp = svc.run_workflow_mock_traced(req)

        db_prompts = db.query(PromptLog).filter(PromptLog.run_id == resp.run_id).all()
        assert len(db_prompts) == 8

    def test_run_workflow_real_dev_exists_but_not_called(self, db: Session):
        """run_workflow_real_dev and run_workflow_real_dev_traced exist with correct signatures."""
        svc = WorkflowExecutionService(db=db)
        assert hasattr(svc, "run_workflow_real_dev")
        assert hasattr(svc, "run_workflow_real_dev_traced")
        
        sig_dev = inspect.signature(svc.run_workflow_real_dev)
        assert "input" in sig_dev.parameters

        sig_traced = inspect.signature(svc.run_workflow_real_dev_traced)
        assert "input" in sig_traced.parameters

    def test_no_external_llm_calls_in_tests(self, db: Session, monkeypatch):
        """Traced full workflow mock run does not invoke external APIs."""
        call_count = {"count": 0}

        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, inp):
            call_count["count"] += 1
            raise RuntimeError("Called real LLM in test")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        svc = WorkflowExecutionService(db=db)
        req = WorkflowTraceRequest(topic="Mock offline multi-pipeline test", workflow_name="full_agent_pipeline", persist_traces=True)
        resp = svc.run_workflow_mock_traced(req)

        assert resp.status == "completed"
        assert call_count["count"] == 0, "run_agent_once was called"
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)
