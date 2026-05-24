"""
AIuthor Backend — LangGraph Workflow Graph Builder (Module 7.2A).

Builds both the 5-node mini_book_pipeline and the 8-node full_agent_pipeline:
  mini_book_pipeline: START → planner → researcher → writer → editor → fact_checker → END
  full_agent_pipeline: START → planner → researcher → writer → humanizer → editor → fact_checker → memory_keeper → assembler → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.workflows.state import AIuthorWorkflowState, workflow_input_to_state, state_to_workflow_output
from app.workflows.nodes import (
    planner_node,
    researcher_node,
    writer_node,
    humanizer_node,
    editor_node,
    fact_checker_node,
    memory_keeper_node,
    assembler_node,
)
from app.workflows.schemas import WorkflowInput, WorkflowOutput, WorkflowInfo, WorkflowTraceRequest
from app.workflows.exceptions import WorkflowExecutionError, WorkflowConfigurationError


# ─── Workflow Metadata Registry ────────────────────────────────────────────────

REGISTERED_WORKFLOWS: dict[str, WorkflowInfo] = {
    "mini_book_pipeline": WorkflowInfo(
        workflow_name="mini_book_pipeline",
        display_name="Mini Book Pipeline",
        description=(
            "A 5-step sequential pipeline: Planner → Researcher → Writer → Editor → Fact Checker. "
            "Generates a short book introduction draft using coordinated agent execution."
        ),
        nodes=["planner", "researcher", "writer", "editor", "fact_checker"],
        enabled=True,
        supports_mock=True,
        supports_real_dev=True,
    ),
    "full_agent_pipeline": WorkflowInfo(
        workflow_name="full_agent_pipeline",
        display_name="Full Agent Pipeline",
        description=(
            "An 8-step sequential pipeline: Planner → Researcher → Writer → Humanizer → Editor → Fact Checker → Memory Keeper → Assembler. "
            "Generates a full compact book outline, draft introduction, memory fingerprint, and final compact package."
        ),
        nodes=["planner", "researcher", "writer", "humanizer", "editor", "fact_checker", "memory_keeper", "assembler"],
        enabled=True,
        supports_mock=True,
        supports_real_dev=True,
    ),
}


MAX_FACT_CHECK_RETRIES = 2


def _fact_check_router(state: AIuthorWorkflowState) -> str:
    """
    Conditional edge after fact_checker_node.
    - If fact_checker flagged unsupported claims AND retry_count < MAX_FACT_CHECK_RETRIES
      → route back to 'writer' for a retry.
    - Otherwise → proceed to 'memory_keeper'.
    """
    fc_out = state.get("fact_checker_output") or {}
    retry_count = state.get("retry_count", 0)

    # Detect failure signal: overall_confidence < 0.7 or any "unsupported"/"flagged" claims
    failed = False
    structured = fc_out.get("structured_output") or {}
    if isinstance(structured, dict):
        confidence = structured.get("overall_confidence", 1.0)
        if confidence < 0.7:
            failed = True
        report = structured.get("fact_check_report", [])
        if any(item.get("status") in ("unsupported", "flagged") for item in report if isinstance(item, dict)):
            failed = True

    if failed and retry_count < MAX_FACT_CHECK_RETRIES:
        return "writer"
    return "memory_keeper"


# ─── Graph Builders ───────────────────────────────────────────────────────────

def build_mini_book_workflow():
    """
    Construct and compile the mini_book_pipeline LangGraph StateGraph.
    """
    graph: StateGraph = StateGraph(AIuthorWorkflowState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("editor", editor_node)
    graph.add_node("fact_checker", fact_checker_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "editor")
    graph.add_edge("editor", "fact_checker")
    graph.add_edge("fact_checker", END)

    return graph.compile()


def build_full_agent_workflow():
    """
    Construct and compile the full_agent_pipeline LangGraph StateGraph.
    """
    graph: StateGraph = StateGraph(AIuthorWorkflowState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("humanizer", humanizer_node)
    graph.add_node("editor", editor_node)
    graph.add_node("fact_checker", fact_checker_node)
    graph.add_node("memory_keeper", memory_keeper_node)
    graph.add_node("assembler", assembler_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "humanizer")
    graph.add_edge("humanizer", "editor")
    graph.add_edge("editor", "fact_checker")
    graph.add_conditional_edges(
        "fact_checker",
        _fact_check_router,
        {"writer": "writer", "memory_keeper": "memory_keeper"},
    )
    graph.add_edge("memory_keeper", "assembler")
    graph.add_edge("assembler", END)

    return graph.compile()


# ─── Individual Runners ───────────────────────────────────────────────────────

def run_mini_book_workflow(
    workflow_input: WorkflowInput | WorkflowTraceRequest,
    execution_mode: str = "mock",
) -> WorkflowOutput:
    """
    Orchestration helper for the 5-node mini_book_pipeline.
    """
    initial_state = workflow_input_to_state(workflow_input, execution_mode=execution_mode)
    compiled_graph = build_mini_book_workflow()

    try:
        final_state: AIuthorWorkflowState = compiled_graph.invoke(initial_state)
    except Exception as exc:
        raise WorkflowExecutionError(
            message=f"LangGraph execution failed: {exc}",
            workflow_name=workflow_input.workflow_name,
            details={"error": str(exc)},
        ) from exc

    return state_to_workflow_output(final_state)


def run_full_agent_workflow(
    workflow_input: WorkflowInput | WorkflowTraceRequest,
    execution_mode: str = "mock",
) -> WorkflowOutput:
    """
    Orchestration helper for the 8-node full_agent_pipeline.
    """
    initial_state = workflow_input_to_state(workflow_input, execution_mode=execution_mode)
    compiled_graph = build_full_agent_workflow()

    try:
        final_state: AIuthorWorkflowState = compiled_graph.invoke(initial_state)
    except Exception as exc:
        raise WorkflowExecutionError(
            message=f"LangGraph execution failed: {exc}",
            workflow_name=workflow_input.workflow_name,
            details={"error": str(exc)},
        ) from exc

    return state_to_workflow_output(final_state)


# ─── Generic Dispatcher Runner ────────────────────────────────────────────────

def run_registered_workflow(
    workflow_input: WorkflowInput | WorkflowTraceRequest,
    execution_mode: str = "mock",
) -> WorkflowOutput:
    """
    Dispatches execution to the corresponding workflow runner based on the input workflow_name.
    """
    name = workflow_input.workflow_name or "mini_book_pipeline"
    if name == "mini_book_pipeline":
        return run_mini_book_workflow(workflow_input, execution_mode)
    elif name == "full_agent_pipeline":
        return run_full_agent_workflow(workflow_input, execution_mode)
    else:
        raise WorkflowConfigurationError(
            message=f"Workflow '{name}' is not registered or supported.",
            workflow_name=name,
        )
