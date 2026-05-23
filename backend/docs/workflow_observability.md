# Workflow Observability & Run Trace Persistence

This document explains the workflow run observability, step trace persistence, and prompt/token cost ledger logging, updated in Module 7.2A to support both `mini_book_pipeline` (5 steps) and `full_agent_pipeline` (8 steps).

---

## Core Concepts

Traced workflows execute multi-agent pipelines and systematically record audit logs for every node execution. This allows developers to inspect, audit, and debug multi-agent graphs:
- **Rendered Prompts**: The precise system and user prompts passed to the underlying LLMs (both mock and real).
- **Agent Outputs**: The structured and raw output content returned from each agent node (planner, researcher, writer, humanizer, editor, fact_checker, memory_keeper, assembler).
- **Duration Metrics**: Fine-grained latency records (duration in milliseconds) for graph speed profiling.
- **Cost & Token Ledger**: Exact tokens processed (input, output, total) and monetary values recorded per step.
- **Error Tracebacks**: Captures unhandled node exceptions and maps them directly to the failing workflow step.

Trace data is written directly to the database using unified observability models (`AgentTrace`, `PromptLog`, `TokenCostLedger`). If database writes fail (e.g. SQLite locks, missing schema), the errors are treated as non-fatal, logged to terminal, and included in step metadata to ensure generation remains completely resilient.

---

## Observability Across Workflows

### 1. `mini_book_pipeline` Tracing
Executes and logs **5 sequential trace steps**:
$$\text{planner} \rightarrow \text{researcher} \rightarrow \text{writer} \rightarrow \text{editor} \rightarrow \text{fact\_checker}$$

### 2. `full_agent_pipeline` Tracing
Executes and logs **8 sequential trace steps**:
$$\text{planner} \rightarrow \text{researcher} \rightarrow \text{writer} \rightarrow \text{humanizer} \rightarrow \text{editor} \rightarrow \text{fact\_checker} \rightarrow \text{memory\_keeper} \rightarrow \text{assembler}$$

For each step, a corresponding `AgentTrace` row is written to the database, linked back to the workflow `run_id`.

---

## API Specification

### 1. Run Traced Workflow in Mock Mode
- **Route**: `POST /api/workflows/mock-run-traced`
- **Request Body (`WorkflowTraceRequest`)**:
  ```json
  {
    "workflow_name": "full_agent_pipeline",
    "topic": "Microservice communication patterns",
    "genre": "technical book",
    "reader_profile": "software engineers",
    "tone": "instructive and concise",
    "persist_traces": true,
    "metadata": {
      "environment": "test"
    }
  }
  ```
- **Response Body (`WorkflowTraceResponse`)**:
  Contains status, execution_mode (`mock`), final_content, and the step list showing linked primary keys (`trace_id`, `prompt_log_id`, `token_cost_id`) alongside the complete serialized `trace_bundle`.

### 2. Live Traced Workflow Execution (Gated)
- **Route**: `POST /api/workflows/dev-run-real-traced`
- **Request Body (`WorkflowTraceRequest`)**:
  ```json
  {
    "workflow_name": "full_agent_pipeline",
    "topic": "Building agentic RAG engines",
    "genre": "technical handbook",
    "reader_profile": "AI architects",
    "persist_traces": true
  }
  ```
- **Response Body (`WorkflowTraceResponse`)**:
  Sequentially executes all 8 agents through live Gemini or OpenAI APIs, records full observability traces, and returns final completed outputs. Requires `ENABLE_REAL_WORKFLOW_TEST_API=true` and valid API keys.

### 3. Retrieve Complete Trace Bundle
- **Route**: `GET /api/workflows/traces/{run_id}`
- **Response Body**:
  Compiles all agent traces, prompt logs, and token ledger costs matching the given run ID in one comprehensive, deep-dictionary bundle.

---

## Verification & Guardrails

- **Mock Execution (Safe for tests)**: Test endpoints run completely offline. They verify that exactly 5 or 8 steps are executed, all schemas are correctly serialized, and database records are committed correctly.
- **External API Gating**: Real endpoints fail with a `403 Forbidden` unless `ENABLE_REAL_WORKFLOW_TEST_API=true` is explicitly set in `.env`.
