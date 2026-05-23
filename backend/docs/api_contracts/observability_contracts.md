# Observability API Contracts

This document describes the HTTP endpoints for backend observability services, including logging and reading traces, prompts, memory operations, token ledger costs, consolidated trace bundles, and cost summaries in the AIuthor backend.

> [!NOTE]
> **Module 4.2C Implemented**: All endpoints below are live.
> **No Agent Execution / LLM calls** are implemented in this module.
> **No LangGraph or workflow engine** is run.
> These endpoints provide backend logging and retrieval services for observability data populated during agent executions.

---

## 1. Agent Trace Endpoints ✅ Implemented (Module 4.2C)

Agent traces track agent execution states (e.g., started, completed, failed), input summaries, and error logs mapped to a specific `BookRun`.

### 1.1 POST `/api/runs/{run_id}/observability/traces`
* **Purpose**: Create a new agent execution trace log.
* **Request Schema**: `AgentTraceCreate`
* **Response Schema**: `AgentTraceResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `run_id` is used as the source of truth. Raises `404` if the book run does not exist.

### 1.2 GET `/api/runs/{run_id}/observability/traces`
* **Purpose**: List agent traces for an execution run (paginated, sorted ascending by `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `agent_name: str | None` — filter by agent name (e.g. `planner`, `researcher`, etc.)
  - `status: str | None` — filter by trace status (e.g. `started`, `completed`, `failed`)
* **Response Schema**: `PaginatedResponse[AgentTraceResponse]`

### 1.3 GET `/api/observability/traces/{trace_id}`
* **Purpose**: Retrieve full details of a specific agent trace.
* **Response Schema**: `AgentTraceResponse`

### 1.4 PATCH `/api/observability/traces/{trace_id}`
* **Purpose**: Partial update of agent trace fields (e.g. marking as completed/failed).
* **Request Schema**: `AgentTraceUpdate`
* **Response Schema**: `AgentTraceResponse`

### 1.5 DELETE `/api/observability/traces/{trace_id}`
* **Purpose**: Permanently delete an agent trace log.
* **Response Schema**: `MessageResponse`

---

## 2. Prompt Log Endpoints ✅ Implemented (Module 4.2C)

Prompt logs capture detailed system prompts, model inputs, and outputs for debugging, audit trails, and generating dossiers.

### 2.1 POST `/api/runs/{run_id}/observability/prompts`
* **Purpose**: Log a detailed system prompt and payload context.
* **Request Schema**: `PromptLogCreate`
* **Response Schema**: `PromptLogResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `run_id` is the source of truth.

### 2.2 GET `/api/runs/{run_id}/observability/prompts`
* **Purpose**: List prompt logs for a run (paginated, sorted newest-first by `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `agent_name: str | None` — filter by linked agent name
  - `model_name: str | None` — filter by model name (e.g. `gpt-4o`, `claude-3-5`)
  - `prompt_name: str | None` — filter by prompt task name
  - `search: str | None` — ILIKE match across prompt text
* **Response Schema**: `PaginatedResponse[PromptLogResponse]`

### 2.3 GET `/api/observability/prompts/{prompt_log_id}`
* **Purpose**: Retrieve details of a prompt log.
* **Response Schema**: `PromptLogResponse`

### 2.4 PATCH `/api/observability/prompts/{prompt_log_id}`
* **Purpose**: Partial update of a prompt log (e.g. adding outputs as asynchronous results return).
* **Request Schema**: `PromptLogUpdate`
* **Response Schema**: `PromptLogResponse`

### 2.5 DELETE `/api/observability/prompts/{prompt_log_id}`
* **Purpose**: Permanently delete a prompt log.
* **Response Schema**: `MessageResponse`

---

## 3. Memory I/O Log Endpoints ✅ Implemented (Module 4.2C)

Memory I/O logs track every read and write operation executed against memory registers to trace context dependencies.

### 3.1 POST `/api/runs/{run_id}/observability/memory-io`
* **Purpose**: Log a memory operation.
* **Request Schema**: `MemoryIOLogCreate`
* **Response Schema**: `MemoryIOLogResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `run_id` is the source of truth.

### 3.2 GET `/api/runs/{run_id}/observability/memory-io`
* **Purpose**: List memory I/O logs for a run (paginated, sorted newest-first by `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `agent_name: str | None` — filter by linked agent name
  - `operation: str | None` — filter by operation type (`read`, `write`, etc.)
  - `memory_type: str | None` — filter by memory subcategory
* **Response Schema**: `PaginatedResponse[MemoryIOLogResponse]`

### 3.3 GET `/api/observability/memory-io/{log_id}`
* **Purpose**: Retrieve memory operation details.
* **Response Schema**: `MemoryIOLogResponse`

### 3.4 DELETE `/api/observability/memory-io/{log_id}`
* **Purpose**: Permanently delete a memory I/O log.
* **Response Schema**: `MessageResponse`
* **Notes**: No `PATCH` endpoint is provided for memory I/O logs as they represent immutable logs of events.

---

## 4. Token Cost Ledger Endpoints ✅ Implemented (Module 4.2C)

Token cost ledger records the exact token inputs, outputs, and estimated pricing in USD (or other currency) per LLM transaction.

### 4.1 POST `/api/runs/{run_id}/observability/token-costs`
* **Purpose**: Log token usage details.
* **Request Schema**: `TokenCostLedgerCreate`
* **Response Schema**: `TokenCostLedgerResponse`
* **Status Code**: `201 Created`
* **Notes**: Path `run_id` is the source of truth. If `total_tokens` is omitted, it is automatically computed as `input_tokens + output_tokens`.

### 4.2 GET `/api/runs/{run_id}/observability/token-costs`
* **Purpose**: List token cost entries for a run (paginated, sorted newest-first by `created_at`).
* **Query Parameters**:
  - `page: int = 1`
  - `page_size: int = 50` (max 100)
  - `agent_name: str | None` — filter by linked agent name
  - `model_name: str | None` — filter by model name
* **Response Schema**: `PaginatedResponse[TokenCostLedgerResponse]`

### 4.3 GET `/api/observability/token-costs/{cost_id}`
* **Purpose**: Retrieve token cost details.
* **Response Schema**: `TokenCostLedgerResponse`

### 4.4 PATCH `/api/observability/token-costs/{cost_id}`
* **Purpose**: Update token cost details.
* **Request Schema**: `TokenCostLedgerUpdate`
* **Response Schema**: `TokenCostLedgerResponse`
* **Notes**: If `input_tokens` or `output_tokens` is modified without providing `total_tokens`, it will automatically recompute `total_tokens`.

### 4.5 DELETE `/api/observability/token-costs/{cost_id}`
* **Purpose**: Permanently delete a token cost entry.
* **Response Schema**: `MessageResponse`

---

## 5. Trace Bundle & Cost Summary Endpoints ✅ Implemented (Module 4.2C)

These endpoints aggregate execution details and compile statistical reports for analysis.

### 5.1 GET `/api/runs/{run_id}/observability/trace-bundle`
* **Purpose**: Compile and export all trace, prompt log, memory operation, and token ledger rows for a run execution.
* **Response Schema**: `TraceBundleResponse`
* **Status Code**: `200 OK`
* **Notes**: Raises `404` if the run is missing. Returns all items sorted properly, along with high-level statistics like total counts of each record type.

### 5.2 GET `/api/runs/{run_id}/observability/cost-summary`
* **Purpose**: Compile aggregate token counts and estimated costs grouped by model breakdown for a run execution.
* **Response Schema**: `RunCostSummaryResponse`
* **Status Code**: `200 OK`
* **Notes**: Summarizes total input/output/total tokens and estimated costs across all ledger rows matching `run_id`, including a sub-breakdown mapped per model name.
