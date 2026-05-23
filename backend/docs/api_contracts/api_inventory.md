# AIuthor Backend — API Inventory

This document serves as the complete inventory of all REST endpoints implemented in the AIuthor API layer (Module 4 complete). All routes listed below are fully implemented, registered, and validated.

---

## 1. Health & Version Endpoints
Exposes service health status and API/app version details.
* **GET** `/health` — Returns backend health status.
* **GET** `/api/version` — Returns application version and environment metadata.

---

## 2. Books Project Endpoints
Handles project metadata and cascading deletions of book projects.
* **POST** `/api/books` — Create a new book project.
* **GET** `/api/books` — List all book projects (paginated, with search and presets filters).
* **GET** `/api/books/{book_id}` — Get single book project details.
* **PATCH** `/api/books/{book_id}` — Partial update of book project settings.
* **DELETE** `/api/books/{book_id}` — Permanently delete a book project (cascades to runs, chapters, etc.).

---

## 3. Book Run Lifecycle Endpoints
Coordinates execution runs, status checks, and lifecycle state transitions.
* **POST** `/api/books/{book_id}/runs` — Create a pending execution run.
* **GET** `/api/books/{book_id}/runs` — List runs for a book project.
* **GET** `/api/runs/{run_id}` — Get single run details.
* **PATCH** `/api/runs/{run_id}` — Partial update of run progress or metadata.
* **GET** `/api/runs/{run_id}/status` — Fetch execution status envelope including progress percentage.
* **POST** `/api/runs/{run_id}/start` — Transition run state to `running`.
* **POST** `/api/runs/{run_id}/complete` — Transition run state to `completed`.
* **POST** `/api/runs/{run_id}/fail` — Transition run state to `failed` with error logging.

---

## 4. Chapters Planning Endpoints
Manages chapter structures, re-ordering sequentially, and layout insertion.
* **POST** `/api/books/{book_id}/chapters` — Create a chapter structure candidate.
* **GET** `/api/books/{book_id}/chapters` — List book project chapters sorted by chapter number.
* **GET** `/api/books/{book_id}/chapters/{chapter_id}` — Get chapter planning details.
* **PATCH** `/api/books/{book_id}/chapters/{chapter_id}` — Partial update of chapter plan.
* **DELETE** `/api/books/{book_id}/chapters/{chapter_id}` — Delete a chapter from outline.
* **POST** `/api/books/{book_id}/chapters/insert` — Insert a chapter at a specific index, sequentially shifting subsequent chapters and flagging `repair_required`.
* **POST** `/api/books/{book_id}/chapters/reorder` — Sequential gaps renumbering (1, 2, 3, etc.).

---

## 5. Book Sections Endpoints
Manages raw text components and default structure sections (front and back matter).
* **POST** `/api/books/{book_id}/sections` — Create a custom book section.
* **GET** `/api/books/{book_id}/sections` — List sections sorted by `sort_order`.
* **GET** `/api/books/{book_id}/sections/{section_id}` — Get section details.
* **PATCH** `/api/books/{book_id}/sections/{section_id}` — Update section metadata or draft.
* **DELETE** `/api/books/{book_id}/sections/{section_id}` — Delete a book section.
* **POST** `/api/books/{book_id}/sections/defaults` — Idempotently create required front and back matter structure candidates.
* **POST** `/api/books/{book_id}/sections/reorder` — Sequential gaps renumbering for sections sort order.

---

## 6. RAG Source Documents & Chunks Endpoints
Handles reference material uploads, window-based text chunking, and lexical search.
* **POST** `/api/books/{book_id}/sources` — Register reference document source metadata.
* **GET** `/api/books/{book_id}/sources` — List source reference documents.
* **GET** `/api/books/{book_id}/sources/{document_id}` — Get source details.
* **PATCH** `/api/books/{book_id}/sources/{document_id}` — Update source status or metadata.
* **DELETE** `/api/books/{book_id}/sources/{document_id}` — Delete source document (cascades to chunks).
* **PATCH** `/api/sources/{document_id}/status` — Status-only update helper.
* **POST** `/api/sources/{document_id}/chunks` — Add a custom text chunk.
* **GET** `/api/sources/{document_id}/chunks` — List chunks for a document.
* **GET** `/api/sources/{document_id}/chunks/{chunk_id}` — Get chunk details.
* **PATCH** `/api/sources/{document_id}/chunks/{chunk_id}` — Update chunk text or properties.
* **DELETE** `/api/sources/{document_id}/chunks/{chunk_id}` — Delete a chunk.
* **PATCH** `/api/chunks/{chunk_id}/embedding-status` — Update embedding registration state.
* **POST** `/api/sources/{document_id}/chunk` — Local character-window text chunker (no LLM required).
* **POST** `/api/rag/retrieve` — Lexical retrieve placeholder (uses case-insensitive substrings).
* **GET** `/api/rag/pgvector-status` — Check pgvector extension availability (Module 6.0B).
* **POST** `/api/chunks/{chunk_id}/embed` — Persist embedding vector for a single chunk (Module 6.0B).
* **POST** `/api/sources/{document_id}/embed-chunks` — Bulk-embed source document chunks (Module 6.0B).
* **POST** `/api/books/{book_id}/embed-chunks` — Bulk-embed all book chunks (Module 6.0B).
* **POST** `/api/rag/semantic-retrieve` — Semantic vector retrieval (Module 6.0B).
* **POST** `/api/rag/hybrid-retrieve` — Hybrid lexical + semantic retrieval (Module 6.1).
* **POST** `/api/rag/context-pack` — Construct agent-ready RAG context pack (Module 6.1).

---

## 7. Memory Registers Endpoints
Keeps continuity across book outline, tone, and character lore through batch registers.
* **POST** `/api/books/{book_id}/memory/read` — Batch read multiple lore or register groups.
* **POST** `/api/books/{book_id}/memory/write` — Batch write multiple lore or register groups in a single transaction.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/memory/facts` — Fact Registry CRUD.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/memory/concepts` — Concept Bible CRUD.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/memory/characters` — Character Bible CRUD.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/memory/callbacks` — Continuity Callbacks CRUD.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/memory/tone-fingerprints` — Tone Fingerprints CRUD.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/memory/decisions` — Project Decisions CRUD.
* **GET** `/api/memory/decisions` — List decisions globally.

---

## 8. Run Observability Endpoints
Enables runtime monitoring of prompts, memory read/write cycles, and API billing costs.
* **POST/GET/PATCH/DELETE** `/api/runs/{run_id}/observability/traces` — Agent call traces.
* **POST/GET/PATCH/DELETE** `/api/runs/{run_id}/observability/prompts` — Prompt payloads and completions logs.
* **POST/GET/DELETE** `/api/runs/{run_id}/observability/memory-io` — Auditing read/write events.
* **POST/GET/PATCH/DELETE** `/api/runs/{run_id}/observability/token-costs` — Billing token usages log.
* **GET** `/api/runs/{run_id}/observability/trace-bundle` — Consolidate all observability records of a run.
* **GET** `/api/runs/{run_id}/observability/cost-summary` — Aggregated billing stats by model breakdown.

---

## 9. Evaluation & File Export Endpoints
Reviews qualitative validation scores and coordinates generated file outputs.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/evals` — Evaluation results.
* **GET** `/api/books/{book_id}/eval-report` — Summary report compile of stored metrics.
* **POST** `/api/runs/{run_id}/evals` — Run-scoped evaluation result log.
* **POST/GET/PATCH/DELETE** `/api/books/{book_id}/exports` — Export records metadata.
* **POST** `/api/books/{book_id}/exports/request` — Request output formats (DOCX, PDF) creation as placeholder records.
* **GET** `/api/books/{book_id}/exports/bundle` — Overview status of all generated outputs.
* **GET** `/api/runs/{run_id}/exports` — List exports for run.

---

## Not Implemented Yet (Postponed to Workflow Modules)
The API layer operates purely as a database-driven CRUD and metadata management backend. The following runtime orchestrations and features will be implemented in subsequent agent/workflow phases:
1. **Real Agent Workflow Execution**: Agents are mock components; no automated background generation exists yet.
2. **LangGraph Orchestration**: The multi-agent workflow graph starts in Module 5.
3. **Real Prompt Completions**: No LLM network calls are made; payload logs are saved as placeholders.
4. **Real Semantic RAG**: Fully implemented using PostgreSQL 16 + pgvector (Module 6.0B) and Hybrid Retrieval + Context Pack (Module 6.1).
5. **Real Evaluation Execution**: Evaluators only summarize recorded logs; no automated quality tests are run.
6. **Real DOCX/PDF Generation**: Export request produces database records with `pending://` URIs; no physical file files are generated on disk.
7. **React User Interface**: The UI resides in a separate client-side bundle.
