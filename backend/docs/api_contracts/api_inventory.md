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

## 10. Agent Execution & Dev-Test Endpoints
Manages agent capability registry queries, local prompt rendering, offline mock executions, and local dev-only manual LLM testing.
* **GET** `/api/agents` — List all registered pipeline agents.
* **GET** `/api/agents/{agent_name}` — Get metadata and prompt template for a single agent.
* **POST** `/api/agents/render-prompt` — Locally render template prompts without calling LLM providers.
* **POST** `/api/agents/mock-run` — Offline mock agent run with deterministic responses.
* **POST** `/api/agents/dev-run-real` — Dev-only single agent run against configured OpenAI/Gemini providers (disabled by default).

---

## 11. LangGraph Workflow Endpoints (Module 7.2A)
Manages LangGraph pipeline registration, offline mock execution, dev-only real LLM workflow testing, and workflow execution trace/cost bundle persistence across multi-agent pipelines (`mini_book_pipeline` and `full_agent_pipeline`).
* **GET** `/api/workflows` — List all registered LangGraph workflows with node metadata (exposes both 5-node and 8-node options).
* **GET** `/api/workflows/{workflow_name}` — Get metadata, node list, and capabilities for a single workflow (supporting `mini_book_pipeline` and `full_agent_pipeline`).
* **POST** `/api/workflows/mock-run` — Run the selected pipeline (`mini_book_pipeline` with 5 nodes or `full_agent_pipeline` with 8 nodes) using MockLLMProvider (offline, no API calls).
* **POST** `/api/workflows/dev-run-real` — Dev-only pipeline run against real Gemini/OpenAI across all 5 or 8 nodes (disabled by default, requires ENABLE_REAL_WORKFLOW_TEST_API=true).
* **POST** `/api/workflows/mock-run-traced` — Run mock workflow with persistent trace, prompt, and cost ledger logging in DB for all executed steps.
* **POST** `/api/workflows/dev-run-real-traced` — Run real dev workflow with persistent trace, prompt, and cost ledger logging in DB (gated, requires ENABLE_REAL_WORKFLOW_TEST_API=true).
* **GET** `/api/workflows/traces/{run_id}` — Retrieve complete consolidated agent trace, prompt log, and token cost ledger bundle for a run ID.

---

## Not Implemented Yet (Postponed to Workflow Modules)
The API layer operates purely as a database-driven CRUD and metadata management backend. The following runtime orchestrations and features will be implemented in subsequent agent/workflow phases:
1. **Full Book Generation**: Background worker pipelines to generate complete books are not built yet.
2. **Real Evaluation Execution**: Evaluators only summarize recorded logs; no automated quality tests are run.
3. **Real DOCX/PDF Generation**: Export request produces database records with `pending://` URIs; no physical file files are generated on disk.
4. **React User Interface**: The UI resides in a separate client-side bundle.
