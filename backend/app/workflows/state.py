"""
AIuthor Backend — Workflow State Definition (Module 7.1A).

Uses TypedDict for LangGraph compatibility.
LangGraph StateGraph requires a TypedDict-compatible state schema.
"""
from __future__ import annotations

from typing import TypedDict, Optional
from app.workflows.schemas import WorkflowInput, WorkflowOutput, WorkflowStepOutput, WorkflowTraceRequest


class AIuthorWorkflowState(TypedDict):
    """
    Complete state structure carried through the AIuthor LangGraph pipeline.
    Each node reads from and writes to this shared state dictionary.
    """
    workflow_name: str
    execution_mode: str          # "mock" | "real_dev"
    run_id: Optional[str]
    book_id: Optional[str]
    chapter_id: Optional[str]
    topic: str
    genre: Optional[str]
    reader_profile: Optional[str]
    tone: Optional[str]
    task: Optional[str]
    context_pack: Optional[dict]
    memory_context: Optional[dict]
    payload: Optional[dict]
    metadata: Optional[dict]
    # Per-agent outputs stored as dicts (serializable AgentOutput)
    planner_output: Optional[dict]
    researcher_output: Optional[dict]
    writer_output: Optional[dict]
    humanizer_output: Optional[dict]
    editor_output: Optional[dict]
    fact_checker_output: Optional[dict]
    memory_keeper_output: Optional[dict]
    assembler_output: Optional[dict]
    # Execution tracking
    steps: list                  # list[dict] — one entry per completed node
    status: str                  # "running" | "completed" | "failed"
    error_message: Optional[str]
    retry_count: int             # number of writer→fact_checker retries so far
    # Tracing & Observability
    persist_traces: bool
    trace_steps: list[dict]
    trace_bundle: Optional[dict]


def workflow_input_to_state(
    input: WorkflowInput | WorkflowTraceRequest,
    execution_mode: str,
) -> AIuthorWorkflowState:
    """
    Convert a WorkflowInput or WorkflowTraceRequest Pydantic schema into the initial AIuthorWorkflowState dict.
    """
    persist = getattr(input, "persist_traces", False)
    return AIuthorWorkflowState(
        workflow_name=input.workflow_name,
        execution_mode=execution_mode,
        run_id=str(input.run_id) if input.run_id else None,
        book_id=str(input.book_id) if input.book_id else None,
        chapter_id=str(input.chapter_id) if input.chapter_id else None,
        topic=input.topic,
        genre=input.genre,
        reader_profile=input.reader_profile,
        tone=input.tone,
        task=getattr(input, "task", None),
        context_pack=input.context_pack,
        memory_context=input.memory_context,
        payload=input.payload,
        metadata=input.metadata or {},
        planner_output=None,
        researcher_output=None,
        writer_output=None,
        humanizer_output=None,
        editor_output=None,
        fact_checker_output=None,
        memory_keeper_output=None,
        assembler_output=None,
        steps=[],
        status="running",
        error_message=None,
        retry_count=0,
        persist_traces=persist,
        trace_steps=[],
        trace_bundle=None,
    )


def state_to_workflow_output(state: AIuthorWorkflowState) -> WorkflowOutput:
    """
    Convert a completed AIuthorWorkflowState into a WorkflowOutput Pydantic response.
    Extracts the final content from the fact_checker or writer output as the top-level result.
    """
    steps = [
        WorkflowStepOutput(**step)
        for step in state.get("steps", [])
    ]

    # Determine final content: prefer assembler > fact_checker > editor > writer > planner
    final_content = None
    for key in ("assembler_output", "fact_checker_output", "editor_output", "writer_output", "planner_output"):
        agent_out = state.get(key)
        if agent_out and agent_out.get("content"):
            final_content = agent_out["content"]
            break

    return WorkflowOutput(
        workflow_name=state["workflow_name"],
        status=state["status"],
        final_content=final_content,
        steps=steps,
        error_message=state.get("error_message"),
        metadata={
            **(state.get("metadata") or {}),
            "execution_mode": state["execution_mode"],
            "topic": state["topic"],
        },
    )
