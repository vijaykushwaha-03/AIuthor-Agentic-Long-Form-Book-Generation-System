# Chapter Generation Loop & Chapter Persistence (Module 8.1)

## Overview

Module 8.1 extends the **relational execution service layers** to support sequential, chapter-by-chapter book drafting using the compiled 8-agent LangGraph workflow (`full_agent_pipeline`). It implements dynamic chapter selection filters, context queries based on customizable RAG templates, text persistence mapping across multiple document columns, and progressive `BookRun` completion tracking.

---

## What the Chapter Generation Loop Does

While the BookRun workflow integration (Module 8.0) coordinates single ad-hoc runs on an entire book project, the **Chapter Generation Loop** sequentially targets planned `Chapter` records. It automates context packing per chapter, triggers independent LangGraph workflow executions, parses timing/step boundaries, maps textual quality tiers back to database fields, and reports overall progress updates.

### Generic Workflow vs. BookRun Workflow vs. Chapter Generation Loop

| Capability | Generic Workflow (`/api/workflows/*`) | Book-Backed Workflow (`/api/books/.../workflow/*`) | Chapter Generation Loop (`/api/books/.../chapters/*`) |
|------------|----------------------------------------|---------------------------------------------------|--------------------------------------------------------|
| **Entity Mapping** | Ad-hoc payload dictionary | Resolves `BookProject` topic/settings | Sequentially loops over target `Chapter` records |
| **Context Extraction** | Explicitly passed JSON | Automatic single RAG context pack | Builds custom RAG context pack per chapter |
| **Persistence Target** | Returns only ephemeral output JSON | Updates `BookRun` record details | Persists step outputs to draft, humanized, edited, and final text columns |
| **Progress Tracking** | None | Switches status between 0% and 100% | Calculates completion percentage iteratively per chapter processed |

---

## Relational Persistence Mapping

To avoid unnecessary migrations and database schema modifications, the service writes execution values directly to the existing model attributes:

### 1. Step-Level Content Persistence
As steps run inside the sequential workflow, the generated texts are persisted in accordance with their quality-tier boundaries:
* `writer` step output $\rightarrow$ **`draft_text`**
* `humanizer` step output $\rightarrow$ **`humanized_text`**
* `editor` step output $\rightarrow$ **`edited_text`**
* `assembler` step output $\rightarrow$ **`final_text`** (which also stores the final prioritised tier text)
* **Word Count**: Estimated dynamically based on the persisted assembler/final string splits: `len(content.split())`.

### 2. Execution Metadata & Parameters
Dynamic configurations are persisted in JSON format within:
* **`chapter_contract`**: Stores execution statistics, timestamps, modes, RAG options, and execution exceptions:
  ```json
  {
    "workflow_name": "full_agent_pipeline",
    "generated_at": "2026-05-23T14:30:00Z",
    "execution_mode": "real_dev",
    "content_source": "full_agent_pipeline",
    "context_pack_used": true,
    "traceable": true,
    "error_message": null
  }
  ```

---

## Chapter Selection & Filtering Rules

The loop identifies target chapters according to three sequential lookup rules:
1. **By explicit ID (`chapter_ids`)**: Iterates precisely over the requested list of chapter IDs. Validates that every ID belongs to the parent book.
2. **By number (`chapter_numbers`)**: Looks up chapters matching specified positive integer numbers (e.g. `[1, 2]`).
3. **All Planned Chapters (Fallback)**: If no selection parameters are supplied in the request body, the service retrieves all planned chapters under the `BookProject`, ordered by `chapter_number` asc.
4. **Limits (`max_chapters`)**: Applies a cropping slice if specified (clamped between 1 and 50).

---

## Status and Progress Lifecycles

### 1. Chapter Statuses
Chapters transition across standard `ChapterStatus` enum states:
* Before run: `planned` or `drafting`
* While running the pipeline graph: **`drafting`**
* Successful complete: **`completed`**
* Exception catch: **`failed`** (with error persisted inside `chapter_contract`)

### 2. BookRun Statuses & Progress
* **Status**: Transitions to `"running"` at start. If all target chapters fail, the run transitions to `"failed"`. If any target chapters complete successfully (even partially), the run transitions to `"completed"`.
* **Progress Percentage**: Updated iteratively in the database after every chapter processed:
  $$\text{progress\_percentage} = \text{round}\left( \frac{\text{completed\_count} + \text{failed\_count} + \text{skipped\_count}}{\text{total\_requested}} \times 100, 2 \right)$$
* **Current Agent**: Summarizes the active task details, e.g. `"generating_chapter_1"` or `"completed"`.

---

## Per-Chapter Context Packing

RAG context queries compile using customized templates mapping the following variables:
* `{book_title}`: Loaded from `BookProject.topic`.
* `{book_topic}`: Loaded from `BookProject.topic`.
* `{chapter_number}`: Active index integer.
* `{chapter_title}`: Active chapter title string.

**Default Query:** `"{book_topic} chapter {chapter_number}: {chapter_title}"`

**Graceful Fallbacks:** If no vector indexes are provisioned or embeddings are missing, the query completes with 0 chunks, logging a RAG notice inside the context metadata without aborting the execution loop.

---

## Developer Setup (Manual Live Gemini Loop Testing)

Live multi-agent loops call external models. They are disabled by default.

### 1. Configuration in `.env`
Add these overrides to your local development environment:
```env
ENABLE_REAL_WORKFLOW_TEST_API=true
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your_real_key>
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Execution POST request
Select chapter numbers or IDs to execute sequentially:
```bash
curl -X POST http://127.0.0.1:8000/api/books/{book_id}/chapters/generate/dev-run-real \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "full_agent_pipeline",
    "chapter_numbers": [1],
    "traced": true,
    "persist_traces": true,
    "build_context_pack": true,
    "persist_chapter_content": true,
    "overwrite_existing": true,
    "context_query_template": "{book_topic} chapter {chapter_number}: {chapter_title}",
    "metadata": {
      "manual_test": true,
      "module": "8.1"
    }
  }'
```

### 3. Retrieve Consolidated Traces
```bash
curl http://127.0.0.1:8000/api/books/{book_id}/chapters/generation-runs/{run_id}/trace
```

---

## 🚫 Constraints & Safety Guards
1. **Disabled by default**: Gated under `enable_real_workflow_test_api` setting; returning `403 Forbidden` on unauthorized production hits.
2. **Offline test runs**: Pytest runs exclusively offline using `MockLLMProvider` and deterministic vectors.
3. **Synchronous orchestration**: Executed synchronously for debugging. No Redis or Celery worker setups are introduced.
