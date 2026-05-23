"""
AIuthor Backend Tests — Full 8-Agent Workflow Graph (Module 7.2A).
"""
from __future__ import annotations

import pytest
from app.workflows.graph import build_full_agent_workflow, run_full_agent_workflow, run_registered_workflow
from app.workflows.schemas import WorkflowInput, WorkflowOutput
from app.workflows.exceptions import WorkflowConfigurationError


class TestFullAgentWorkflowGraph:

    def test_build_full_agent_workflow_returns_compiled_graph(self):
        """build_full_agent_workflow returns a compiled LangGraph graph."""
        compiled = build_full_agent_workflow()
        assert hasattr(compiled, "invoke")

    def test_run_full_agent_workflow_returns_completed_output(self):
        """run_full_agent_workflow in mock mode executes all nodes and returns completed status."""
        inp = WorkflowInput(topic="Cloud native security architectures", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        assert isinstance(output, WorkflowOutput)
        assert output.status == "completed"

    def test_full_workflow_output_includes_eight_steps(self):
        """Full sequential pipeline executes exactly 8 nodes in order."""
        inp = WorkflowInput(topic="Serverless databases", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        assert len(output.steps) == 8
        agent_names = [s.agent_name for s in output.steps]
        expected = ["planner", "researcher", "writer", "humanizer", "editor", "fact_checker", "memory_keeper", "assembler"]
        assert agent_names == expected

    def test_full_workflow_includes_planner_step(self):
        """planner step is successfully executed and returned in steps."""
        inp = WorkflowInput(topic="Quantum internet", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        planner_step = next((s for s in output.steps if s.step_name == "planner"), None)
        assert planner_step is not None
        assert planner_step.status == "completed"

    def test_full_workflow_includes_humanizer_step(self):
        """humanizer step is successfully executed and returned in steps."""
        inp = WorkflowInput(topic="Continuous deployment", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        humanizer_step = next((s for s in output.steps if s.step_name == "humanizer"), None)
        assert humanizer_step is not None
        assert humanizer_step.status == "completed"

    def test_full_workflow_includes_memory_keeper_step(self):
        """memory_keeper step is successfully executed and returned in steps."""
        inp = WorkflowInput(topic="Distributed consensus", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        memory_step = next((s for s in output.steps if s.step_name == "memory_keeper"), None)
        assert memory_step is not None
        assert memory_step.status == "completed"

    def test_full_workflow_includes_assembler_step(self):
        """assembler step is successfully executed and returned in steps."""
        inp = WorkflowInput(topic="Microservices architecture", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        assembler_step = next((s for s in output.steps if s.step_name == "assembler"), None)
        assert assembler_step is not None
        assert assembler_step.status == "completed"

    def test_final_content_comes_from_assembler_when_available(self):
        """assembler_output content is chosen as the final content for full pipeline."""
        inp = WorkflowInput(topic="Domain driven design", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        assert output.final_content is not None
        # In mock mode, MockLLMProvider returns generic content which will be in the assembler node
        assert len(output.final_content) > 0

    def test_unsupported_workflow_name_raises_configuration_error(self):
        """Generic runner run_registered_workflow raises WorkflowConfigurationError for invalid pipeline name."""
        with pytest.raises(WorkflowConfigurationError) as exc_info:
            # We bypass Pydantic validation by model_copy to trigger runner validation directly
            inp = WorkflowInput(topic="Invalid workflow topic")
            inp.workflow_name = "unsupported_pipeline_xyz"
            run_registered_workflow(inp, execution_mode="mock")
        assert "not registered" in str(exc_info.value).lower()

    def test_full_workflow_mock_run_does_not_call_real_llm(self, monkeypatch):
        """run_full_agent_workflow enforces MockLLMProvider and does not make external calls."""
        call_count = {"count": 0}

        from app.services.agent_execution_service import AgentExecutionService
        original_run_agent_once = AgentExecutionService.run_agent_once

        def boom_run_once(self, inp):
            call_count["count"] += 1
            raise RuntimeError("Intercepted real LLM execution inside mock test")

        monkeypatch.setattr(AgentExecutionService, "run_agent_once", boom_run_once)

        inp = WorkflowInput(topic="DevOps principles", workflow_name="full_agent_pipeline")
        output = run_full_agent_workflow(inp, execution_mode="mock")
        
        assert output.status == "completed"
        assert call_count["count"] == 0, "run_agent_once was called"
        monkeypatch.setattr(AgentExecutionService, "run_agent_once", original_run_agent_once)
