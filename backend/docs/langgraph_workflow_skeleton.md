# AIuthor Backend — LangGraph Workflow Skeleton (Module 7.2A)

## Overview

Module 7.2A expands the **LangGraph workflow foundation** to support both the original 5-node sequential pipeline (`mini_book_pipeline`) and the complete 8-node sequential pipeline (`full_agent_pipeline`). It introduces state fields for humanizer, memory keeper, and assembler nodes, provides adaptive node transitions, and implements a unified dispatcher that dynamically executes pipelines and persists observation logs.

---

## Architecture

AIuthor supports two production-ready multi-agent workflows compiled dynamically via the graph layer:

### 1. `mini_book_pipeline` (5-Node Sequential)
```
START → planner → researcher → writer → editor → fact_checker → END
```
*Purpose*: Quick drafts or simplified runs. The fact_checker node acts as the terminal step, transitioning state to completed and extracting final content.

### 2. `full_agent_pipeline` (8-Node Sequential)
```
START → planner → researcher → writer → humanizer → editor → fact_checker → memory_keeper → assembler → END
```
*Purpose*: Fully humanized, compiled long-form generation. Coordinated execution of all 8 pipeline agents, ending with the assembler node which packages and produces the final content.

---

## Package Structure

```
backend/
├── app/
│   ├── workflows/
│   │   ├── __init__.py              # Re-exports all public symbols
│   │   ├── schemas.py               # Pydantic validation schemas (with workflow_name check)
│   │   ├── exceptions.py            # WorkflowError hierarchy (WorkflowConfigurationError subclass)
│   │   ├── state.py                 # AIuthorWorkflowState TypedDict + priority helpers
│   │   ├── nodes.py                 # 8 wrapper functions (including humanizer, memory_keeper, assembler)
│   │   └── graph.py                 # Double StateGraph builder + generic dispatcher runner
│   ├── services/
│   │   └── workflow_execution_service.py   # Service layer (fully decoupled & dynamically routed)
│   └── api/
│       └── routes_workflows.py      # FastAPI router for /api/workflows/*
├── docs/
│   └── langgraph_workflow_skeleton.md      # This file
└── tests/
    ├── test_full_agent_workflow_graph.py
    ├── test_workflow_service_full_pipeline.py
    ├── test_workflows_full_pipeline_api.py
    └── test_api_layer_complete.py
```

---

## Key Components

### `AIuthorWorkflowState` (TypedDict)

LangGraph-compatible state that carries inputs and per-node outputs across both pipelines:

```python
class AIuthorWorkflowState(TypedDict):
    workflow_name: str
    execution_mode: str              # "mock" | "real_dev"
    topic: str
    genre: Optional[str]
    reader_profile: Optional[str]
    tone: Optional[str]
    context_pack: Optional[dict]
    memory_context: Optional[dict]
    
    # 8-agent execution outputs
    planner_output: Optional[dict]
    researcher_output: Optional[dict]
    writer_output: Optional[dict]
    humanizer_output: Optional[dict]
    editor_output: Optional[dict]
    fact_checker_output: Optional[dict]
    memory_keeper_output: Optional[dict]
    assembler_output: Optional[dict]
    
    steps: list
    status: str                      # "running" | "completed" | "failed"
    error_message: Optional[str]
```

### Adaptive Final Content Extraction

Content extraction strictly prioritizes quality/polishing tiers based on the selected pipeline:
$$\text{assembler\_output} > \text{fact\_checker\_output} > \text{writer\_output}$$

```python
def select_final_content(state: AIuthorWorkflowState) -> Optional[str]:
    # 1. Highest priority: Assembler polished package
    if state.get("assembler_output") and state["assembler_output"].get("content"):
        return state["assembler_output"]["content"]
    # 2. Medium priority: Fact Checker validated text
    if state.get("fact_checker_output") and state["fact_checker_output"].get("content"):
        return state["fact_checker_output"]["content"]
    # 3. Fallback: Writer draft
    if state.get("writer_output") and state["writer_output"].get("content"):
        return state["writer_output"]["content"]
    return None
```

### The 8 Workflow Nodes

Each node function leverages `execute_agent_node` to coordinate execution, wrap exceptions, record duration, log tokens, and save log states.

1. **`planner_node`**: Orchestrates initial book blueprint, outline, and target chapters structure.
2. **`researcher_node`**: Extracts facts, citations, and evidence packs matching outline sections.
3. **`writer_node`**: Formulates publication-quality chapter text embedded with citations.
4. **`humanizer_node`**: Modulates emotional resonance, tone fingerprint, and stylistic naturalness.
5. **`editor_node`**: Corrects formatting, flow, smooth transitions, and architectural structure.
6. **`fact_checker_node`**: Validates citations, verifies grounding assertions, and flags unsupported claims.
7. **`memory_keeper_node`**: Builds core memory models, callbacks, and tracks recurring motifs.
8. **`assembler_node`**: Assembles components into the final compiled text package.

---

## Dynamic Routing & Dispatching

The workflow execution service determines the pipeline based on request parameters and dynamically routes execution:

```python
# Service handles both pipelines transparently:
svc = WorkflowExecutionService(db)

# 1. Mock Runs (Safe for CI/CD)
mock_output = svc.run_workflow_mock(WorkflowInput(topic="AI", workflow_name="full_agent_pipeline"))

# 2. Live Dev Runs (Gated behind ENABLE_REAL_WORKFLOW_TEST_API)
real_output = svc.run_workflow_real_dev(WorkflowInput(topic="AI", workflow_name="full_agent_pipeline"))
```

---

## Test Verification

Both workflows are 100% offline-verifiable. The suite includes:
- **`test_full_agent_workflow_graph.py`**: Validates StateGraph structure, compiled routing logic, and node results.
- **`test_workflow_service_full_pipeline.py`**: Verifies dynamic dispatching, database persistence, and no-LLM boundaries.
- **`test_workflows_full_pipeline_api.py`**: Tests routing endpoints, validation errors, and 403 gates.

**All 893 automated backend unit and integration tests run offline with MockLLMProvider and MockEmbeddingProvider.**
