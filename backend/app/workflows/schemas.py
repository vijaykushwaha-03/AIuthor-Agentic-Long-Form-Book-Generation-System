"""
AIuthor Backend — Workflow Pydantic Schemas (Module 7.1A).
"""
from __future__ import annotations

from uuid import UUID
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema


class WorkflowInput(BaseSchema):
    """
    Input model required to invoke any AIuthor workflow pipeline.
    """
    workflow_name: str = "mini_book_pipeline"
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    topic: str = Field(..., min_length=1)
    genre: str | None = None
    reader_profile: str | None = None
    tone: str | None = None
    task: str | None = None
    context_pack: dict | None = None
    memory_context: dict | None = None
    payload: dict | None = None
    metadata: dict | None = None

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v not in ["mini_book_pipeline", "full_agent_pipeline"]:
            from app.workflows.exceptions import WorkflowConfigurationError
            raise WorkflowConfigurationError(
                message=f"Workflow '{v}' is not registered or supported.",
                workflow_name=v,
            )
        return v


class WorkflowStepOutput(BaseSchema):
    """
    Output from a single agent node execution within the workflow.
    """
    step_name: str
    agent_name: str
    status: str
    content: str | None = None
    structured_output: dict | None = None
    error_message: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict | None = None


class WorkflowOutput(BaseSchema):
    """
    Final output returned after a complete workflow execution.
    """
    workflow_name: str
    status: str
    final_content: str | None = None
    steps: list[WorkflowStepOutput] = Field(default_factory=list)
    error_message: str | None = None
    metadata: dict | None = None


class WorkflowInfo(BaseSchema):
    """
    Metadata descriptor summarizing a registered workflow's capabilities.
    """
    workflow_name: str
    display_name: str
    description: str
    nodes: list[str] = Field(default_factory=list)
    enabled: bool = True
    supports_mock: bool = True
    supports_real_dev: bool = True


class WorkflowTraceRequest(BaseSchema):
    """
    Input model required to invoke any AIuthor workflow pipeline with trace logging enabled.
    """
    workflow_name: str = "mini_book_pipeline"
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    topic: str = Field(..., min_length=1)
    genre: str | None = None
    reader_profile: str | None = None
    tone: str | None = None
    context_pack: dict | None = None
    memory_context: dict | None = None
    payload: dict | None = None
    metadata: dict | None = None
    persist_traces: bool = True

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, v: str) -> str:
        if v not in ["mini_book_pipeline", "full_agent_pipeline"]:
            from app.workflows.exceptions import WorkflowConfigurationError
            raise WorkflowConfigurationError(
                message=f"Workflow '{v}' is not registered or supported.",
                workflow_name=v,
            )
        return v


class WorkflowTraceStep(BaseSchema):
    """
    Individual step execution trace log entry recorded in a workflow run.
    """
    step_name: str
    agent_name: str
    status: str
    trace_id: UUID | None = None
    prompt_log_id: UUID | None = None
    token_cost_id: UUID | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    error_message: str | None = None
    content_preview: str | None = None
    metadata: dict | None = None


class WorkflowTraceResponse(BaseSchema):
    """
    Aggregated response returned by the traced workflow execution engine.
    """
    workflow_name: str
    status: str
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    execution_mode: str
    final_content: str | None = None
    steps: list[WorkflowTraceStep] = Field(default_factory=list)
    trace_bundle: dict | None = None
    error_message: str | None = None
    metadata: dict | None = None

