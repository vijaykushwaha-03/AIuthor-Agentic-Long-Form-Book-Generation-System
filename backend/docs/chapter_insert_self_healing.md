# Module 8.2 — Chapter Insert & Self-Healing Repair

## Overview

Module 8.2 provides a fully resilient chapter insertion and self-healing repair
pipeline. When a new chapter is inserted into an existing book, the system
automatically detects and repairs structural inconsistencies across the entire
book project.

## Self-Healing Repairs

When a chapter is inserted, the following repair sub-systems activate:

### 1. Chapter Numbering Verification
- Detects gaps or duplicates in the `chapter_number` sequence
- Reorders all chapters sequentially (1, 2, 3, ..., N)
- Logs the before/after numbering state in `StructureRepairItem`

### 2. Table of Contents (TOC) Repair
- Locates the `BookSection` with `section_type = "toc"`
- Rebuilds TOC content from the current ordered chapter list
- Updates section metadata with repair audit information
- Skips gracefully if no TOC section exists

### 3. Cross-Chapter Callback Repair
- Queries all `CallbackIndex` records for the book
- Shifts `source_chapter` and `target_chapter` numbers >= insert position
- Stores callback repair metadata in the inserted chapter's `chapter_contract`

### 4. Glossary / Concept Bible Repair
- Queries all `ConceptBible` records for the book
- Shifts `first_chapter` and entries in `appears_in_chapters` lists
- Logs each concept shift as a separate `StructureRepairItem`

### 5. Back Matter Section Repair
- Updates metadata audit logs on `BookSection` records with
  `section_type` in (`glossary`, `references`, `appendix`, `index`)
- Skips gracefully if no back matter sections exist

## Resilient Design

Each repair sub-system runs independently inside a `try-except` block. A failure
in one repair (e.g., TOC) will **not** prevent other repairs (callbacks, glossary)
from executing. Failed repairs are logged as `StructureRepairItem` entries with
`status = "failed"`.

## Content Generation

Optionally, the inserted chapter can be generated through the `full_agent_pipeline`
workflow (8-agent LangGraph pipeline). This supports:

- **Mock mode** — Offline execution using `MockLLMProvider`
- **Real dev mode** — Live Gemini/OpenAI execution (gated by `ENABLE_REAL_WORKFLOW_TEST_API`)
- **Traced mode** — Full agent step trace, prompt log, and token cost persistence

## API Endpoints

### POST `/api/books/{book_id}/chapters/insert-repair/mock-run`
Execute mock chapter insertion + self-healing repair (offline).

### POST `/api/books/{book_id}/chapters/insert-repair/dev-run-real`
Execute live Gemini/OpenAI chapter insertion + self-healing repair.
Gated by `ENABLE_REAL_WORKFLOW_TEST_API=true`.

### GET `/api/books/{book_id}/chapters/insert-repair/runs/{run_id}/trace`
Fetch trace bundle (agent traces, prompt logs, token costs) for a repair run.

## Request Schema

```json
{
    "book_id": "uuid",
    "run_id": "uuid (optional, auto-created if missing)",
    "insert_at_chapter_number": 2,
    "title": "New Chapter Title",
    "summary": "Brief purpose of the new chapter",
    "generate_content": true,
    "workflow_name": "full_agent_pipeline",
    "execution_mode": "mock",
    "traced": true,
    "persist_traces": true,
    "build_context_pack": true,
    "repair_toc": true,
    "repair_callbacks": true,
    "repair_glossary": true,
    "repair_back_matter": true,
    "overwrite_existing_repair": true
}
```

## Response Schema

```json
{
    "book_id": "uuid",
    "run_id": "uuid",
    "inserted_chapter_id": "uuid",
    "inserted_chapter_number": 2,
    "workflow_name": "full_agent_pipeline",
    "execution_mode": "mock",
    "status": "completed",
    "generated_content_preview": "First 1000 chars...",
    "repair_items": [
        {
            "item_type": "numbering",
            "status": "success",
            "message": "Chapter sequence verified..."
        },
        {
            "item_type": "toc",
            "status": "success",
            "message": "TOC updated..."
        }
    ],
    "affected_chapter_ids": ["uuid1", "uuid2"],
    "toc_repaired": true,
    "callbacks_repaired": true,
    "glossary_repaired": true,
    "back_matter_repaired": true,
    "trace_bundle": { ... },
    "metadata": { ... }
}
```

## Test Coverage

| Test File | Tests | Scope |
|-----------|-------|-------|
| `test_chapter_self_healing_service.py` | 16 | Unit tests for service layer |
| `test_chapter_self_healing_api.py` | 10 | Integration tests for API routes |
| `test_api_layer_complete.py` | Updated | OpenAPI endpoint registration |
