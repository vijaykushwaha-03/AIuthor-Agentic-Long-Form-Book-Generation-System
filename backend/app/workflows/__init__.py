"""
AIuthor Backend — Workflow Package (Module 7.1A).
"""
from app.workflows.schemas import (
    WorkflowInput,
    WorkflowOutput,
    WorkflowStepOutput,
    WorkflowInfo,
    WorkflowTraceRequest,
    WorkflowTraceStep,
    WorkflowTraceResponse,
)
from app.workflows.exceptions import WorkflowError, WorkflowConfigurationError, WorkflowExecutionError
from app.workflows.state import AIuthorWorkflowState, workflow_input_to_state, state_to_workflow_output
from app.workflows.graph import build_mini_book_workflow, run_mini_book_workflow, REGISTERED_WORKFLOWS

__all__ = [
    # schemas
    "WorkflowInput",
    "WorkflowOutput",
    "WorkflowStepOutput",
    "WorkflowInfo",
    "WorkflowTraceRequest",
    "WorkflowTraceStep",
    "WorkflowTraceResponse",
    # exceptions
    "WorkflowError",
    "WorkflowConfigurationError",
    "WorkflowExecutionError",
    # state
    "AIuthorWorkflowState",
    "workflow_input_to_state",
    "state_to_workflow_output",
    # graph
    "build_mini_book_workflow",
    "run_mini_book_workflow",
    "REGISTERED_WORKFLOWS",
]
