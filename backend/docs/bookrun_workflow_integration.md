# BookRun Workflow Integration (Module 8.0)

## Overview

Module 8.0 introduces the **BookRun Workflow Integration** layer. This layer connects multi-agent dynamic LangGraph sequential execution graphs with database-backed relational records (`BookProject`, `BookRun`, and `Chapter`). It enables execution runs to fetch configurations directly from existing projects, map properties, build dynamic RAG context packs, and persist step execution traces linked back to the database entities.

---

## Generic vs. Book-Backed Workflows

| Metric | Generic Workflows (`/api/workflows/*`) | Book-Backed Workflows (`/api/books/{book_id}/workflow/*`) |
|--------|----------------------------------------|---------------------------------------------------------|
| **Data Scope** | Independent, ad-hoc payloads | Securely scoped to database-backed relational entities |
| **Project Context** | Explicitly supplied in JSON body | Implicitly loaded from `BookProject` settings |
| **Run Persistence** | Observability traces only | Connects to `BookRun` record, updating state and progress |
| **Context Packing** | Standard text or manual dictionary | Automatic hybrid RAG packing using `ContextPackService` |

---

## Technical Architecture & Database Mapping

### 1. Data Mapping Flow

When a workflow run is triggered, the `BookRunWorkflowService` automatically maps properties from the database models into a `WorkflowInput` or `WorkflowTraceRequest`:

- **topic**: Loaded from `BookProject.topic`.
- **genre**: Loaded from `BookProject.genre`.
- **reader_profile**: Loaded from `BookProject.reader_profile`.
- **tone**: Loaded from `BookProject.tone`.
- **run_id**: Populated with the active `BookRun.id`.
- **book_id**: Populated with the active `BookProject.id`.
- **chapter_id**: Scoped to the `Chapter.id` (if supplied).

### 2. Context Pack Construction

If `build_context_pack` is enabled:
1. It looks for a user-provided `context_query` override in the request.
2. If none is supplied, it compiles a query dynamically: `"{book.topic} {chapter.title}"`.
3. It calls `ContextPackService` to retrieve lexical and semantic matches.
4. **Resiliency Guardrail**: If no embedded chunks exist in the RAG store (or database is empty), it recovers gracefully, inserts a note in the pack metadata (`"No context chunks found. Workflow ran without RAG context."`), and continues executing without failing.

### 3. Trace Relationship Links

Observability traces systematically link back to database entities:
- Every `AgentTrace` row matches `run_id` and `book_id`.
- Every `PromptLog` and `TokenCostLedger` entry maps to `run_id` and `book_id`.
- Steps map correctly within dynamic routing boundaries, allowing complete trace bundles to be retrieved scoping the book's history.

---

## BookRun Status Lifecycle Transitions

Execution status transitions are securely managed through `BookRunService` methods:
- **Prior to Node Execution**: Transition run status to `"running"`, set `started_at` timestamp, and update `current_agent = "workflow_start"`.
- **Upon Success**: Transition run status to `"completed"`, set `completed_at`, clear `current_agent = "completed"`, and record `progress_percentage = 100.0` in metadata.
- **Upon Failure**: Transition run status to `"failed"`, set `completed_at`, and record the unhandled exception text in `error_message`.

---

## Gated Developer Setup (Manual Live Gemini Testing)

Live Gemini and OpenAI multi-agent book executions call external LLMs and incur cost. They are disabled by default.

### 1. Configuration in `.env`
Add these overrides to your local development environment:
```env
ENABLE_REAL_WORKFLOW_TEST_API=true
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your_real_credentials>
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Live Run Endpoint Execution
Create a book project and issue a synchronous POST:
```bash
curl -X POST http://127.0.0.1:8000/api/books/{book_id}/workflow/dev-run-real \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "full_agent_pipeline",
    "traced": true,
    "persist_traces": true,
    "build_context_pack": true,
    "metadata": {
      "manual_test": true
    }
  }'
```

### 3. Retrieve Bundle
Get compiled cost ledgers, prompts, and timing audits:
```bash
curl http://127.0.0.1:8000/api/books/{book_id}/workflow/runs/{run_id}/trace
```

---

## 🚫 Critical Constraints & Safety Guards

1. **Gated by Default**: `POST /api/books/{book_id}/workflow/dev-run-real` returns a `403 Forbidden` unless real workflow tests are explicitly enabled.
2. **Synchronous Execution**: Workflow calls execute synchronously to allow immediate debugging. No Celery worker processes or asynchronous thread loops are added.
3. **No Generation Loops**: This module implements single-execution workflow hooks. Full recursive chapter-by-chapter book generations and file exports (DOCX/PDF) are deferred.
4. **No Database Migrations**: No models were modified and no migrations are required.
