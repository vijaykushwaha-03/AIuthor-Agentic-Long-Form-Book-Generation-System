# AIuthor Backend — Developer Reference

This directory contains the FastAPI backend code, database configurations, migrations, prompts, and testing suites.

## PostgreSQL 16 + pgvector Verification
To check and verify the pgvector vector store readiness:
* Run the migrations to synchronize your schema and HNSW indexes:
  ```powershell
  alembic upgrade head
  ```
* Run the verification and audit script:
  ```powershell
  python scripts/check_pgvector_embedding.py
  ```
* Confirm that the `embedding` column on the `document_chunks` table is natively defined as a `vector(768)` type (and not json/jsonb/text fallback).
* Note: The SQLite JSON fallback is strictly for testing/offline mock environments. Real vector operations on PostgreSQL will utilize native `pgvector` operators and indexes.

## Project Progress Status

### ✅ Module 6.1 Completed: Hybrid Retrieval + Context Pack Builder
- **Hybrid Retrieval Service** (`HybridRetrievalService`) added, combining case-insensitive lexical exact phrase/term-overlap matching and semantic vector similarity search.
- **Context Pack Service** (`ContextPackService`) added, formatting hybrid RAG matches into stable, citation-annotated context blocks with size-boundary character limits and re-indexing.
- **Advanced score merging** implemented with customizable weights: $combined\_score = semantic\_score \times semantic\_weight + lexical\_score \times lexical\_weight$ (filtering out zero scores).
- **New Pydantic schemas** added: `HybridRetrievalRequest`, `ContextPackRequest`, `CitationItem`, `ContextChunk`, `HybridRetrievalResponse`, `ContextPackResponse`.
- **API endpoints registered separately**:
  - `POST /api/rag/hybrid-retrieve`
  - `POST /api/rag/context-pack`
- **Comprehensive offline testing**: Added 33 unit and integration tests across `test_hybrid_retrieval_service.py`, `test_context_pack_service.py`, and `test_rag_hybrid_context_api.py`.
- **Constraints Confirmed:**
  - 🚫 No database migrations created.
  - 🚫 No real external LLM or embedding API calls in tests.
  - 🚫 No background agents or LangGraph orchestrations added.
  - 🚫 Original lexical (`POST /api/rag/retrieve`) and semantic (`POST /api/rag/semantic-retrieve`) endpoints preserved completely.

---

### ✅ Module 6.0A Completed: pgvector + Embedding Provider Foundation
- **Embedding provider abstraction** added with unified `EmbeddingRequest` / `EmbeddingResponse` / `EmbeddingItem` / `EmbeddingProviderInfo` schemas.
- **Gemini embedding provider** added as **default** (`EMBEDDING_PROVIDER=gemini`, model `text-embedding-004`, 768 dims).
- **OpenAI embedding provider** support added (`EMBEDDING_PROVIDER=openai`, model `text-embedding-3-small`, 1536 dims).
- **Mock embedding provider** added — deterministic SHA-256 hash vectors, no network, used in all tests.
- **Factory pattern** (`get_embedding_provider()`) resolves provider from env var or explicit argument.
- **`EmbeddingService`** wrapper added to `app/services/` as the stable business-logic interface.
- **API routes** added: `GET /api/embeddings/provider` (status) and `POST /api/embeddings/mock` (contract testing).
- **pgvector readiness utilities** added (`app/db/pgvector_check.py`) — safe read-only checks, graceful on SQLite.
- **`pgvector==0.3.2`** added to `requirements.txt`.
- **Constraints Confirmed:**
  - 🚫 No vector column migration added.
  - 🚫 No semantic retrieval added.
  - 🚫 No chunk embedding job added.
  - 🚫 No external embedding calls in tests.
  - 🚫 No agents or LangGraph added.
  - 🚫 No database migrations created.

---

### ✅ Module 5.0 Completed: LLM Provider Abstraction Layer
- **LLM provider abstraction** added with unified `LLMRequest` / `LLMResponse` / `LLMMessage` schemas.
- **Gemini provider** added as the **default** provider (`LLM_PROVIDER=gemini`, model `gemini-2.5-flash`).
- **OpenAI/GPT provider** support added (`LLM_PROVIDER=openai`, model `gpt-4o-mini`).
- **Mock provider** added for fully offline tests — no API key required.
- **Factory pattern** (`get_llm_provider()`) resolves provider from env var or explicit argument.
- **`LLMService`** wrapper added to `app/services/` as the stable business-logic interface.
- **API routes** added: `GET /api/llm/provider` (status) and `POST /api/llm/mock-generate` (contract testing).
- **34 new tests** added across `test_llm_provider_layer.py` and `test_llm_api.py`.
- **Constraints Confirmed:**
  - 🚫 No agents or LangGraph added.
  - 🚫 No real LLM generation endpoint (mock-generate only).
  - 🚫 No external LLM calls in tests.
  - 🚫 No database migrations created.
  - 🚫 No pgvector / embeddings added.

---

### Module 4 Completed: API + Service Layer
- **Unified Services & API Endpoints**: All service classes (`BookProjectService`, `BookRunService`, `ChapterService`, `BookSectionService`, `SourceDocumentService`, `DocumentChunkService`, `MemoryService`, `ObservabilityService`, `EvalService`, `ExportService`) and corresponding REST routes are fully completed, registered, and integrated.
- **API Groups Completed**:
  - Book/run project lifecycle and envelope status tracking.
  - Chapter re-ordering/insertion algorithms and default sections structures.
  - reference source document loaders, window-based text chunkers, and placeholder case-insensitive lexical search.
  - persistent bibles for concept candidates, continuity callbacks index, characters lore, tone fingerprints, and decisions registers.
  - run observability logs (prompt inputs/outputs auditing, billing costs tracking, execution trace bundles, cost stats aggregators).
  - validations and format export records (score averages report compilation, placeholder requests creating `pending://` virtual URIs).
- **Verifications & Contract Docs**:
  - Technical REST contracts documented across 7 detailed files under `docs/api_contracts/`.
  - Comprehensive API inventory cataloging all 60+ endpoints.
  - Final API-layer smoke tests verifying module imports, registration, schema loading, and Starlette route evaluation ordering to safeguard static paths from dynamic UUID swallowed conflicts.
- **Constraints Confirmed**:
  - 🚫 **No agents or LangGraph workflow orchestration** implemented yet (mocked/postponed).
  - 🚫 **No pgvector or vector databases embeddings** implemented yet (deferred to Module 6).
  - 🚫 **No real evaluations or file generators** implemented yet; no physical files written on disk.
  - 🚫 **No database migrations** were created during Module 4 routing layer construction.

---

### Module 2.2 Completed (Core Book Tables)
- **BookProject** model added
- **BookRun** model added
- **Chapter** model added
- **BookSection** model added
- Alembic migration created and successfully run
- Core book tables migrated and verified

### Module 2.3A Completed (RAG Source Tables Without pgvector)
- **SourceDocument** model added
- **DocumentChunk** model added
- Alembic migration created and successfully run
- RAG source tables migrated and verified
- pgvector setup still postponed to Module 6

### Module 2.3B Completed (Memory Tables)
- **FactRegistry** model added
- **ConceptBible** model added
- **CharacterBible** model added
- **CallbackIndex** model added
- **ToneFingerprint** model added
- **DecisionLog** model added
- Alembic migration created and successfully run
- Memory tables migrated and verified

### Module 2.4A Completed (Observability Tables)
- **AgentTrace** model added
- **PromptLog** model added
- **MemoryIOLog** model added
- **TokenCostLedger** model added
- Alembic migration created and successfully run
- Observability tables migrated and verified

### Module 2.4B Completed (Eval + Export Tables)
- **EvalResult** model added
- **ExportFile** model added
- Alembic migration created and successfully run
- Eval/export tables migrated and verified

### Module 3.1 Completed (Pydantic Schema Foundation)
- **Schemas Package** created under `backend/app/schemas/`
- **Base schemas** (`BaseSchema`, `IDSchema`, `TimestampSchema`, `ORMBaseSchema`) added
- **Shared enums** (`TonePreset`, `BookStatus`, `RunStatus`, etc.) added
- **Common schemas** (`PaginationParams`, `PaginatedResponse`, etc.) added
- **Error schemas** (`ErrorResponse`, `ValidationErrorResponse`, `InternalErrorResponse`) added
- **Unit tests** created and successfully run
- **Existing health/version routes** aligned to the schemas package
- No database model changes or Alembic migrations created

### Module 3.2A Completed (Book Project & Book Run Schemas)
- **BookProject schemas** (`BookProjectCreate`, `BookProjectUpdate`, `BookProjectResponse`, `BookProjectListItem`) added
- **BookRun schemas** (`BookRunCreate`, `BookRunStartRequest`, `BookRunUpdate`, `BookRunResponse`, `BookRunStatusResponse`) added
- **Validation tests** added and verified
- No API routes or database migrations added

### Module 3.2B Completed (Chapter & Book Section Schemas)
- **Chapter schemas** (`ChapterContract`, `ChapterCreate`, `ChapterUpdate`, `ChapterResponse`, `ChapterListItem`, `ChapterInsertRequest`) added
- **BookSection schemas** (`BookSectionCreate`, `BookSectionUpdate`, `BookSectionResponse`, `BookSectionListItem`) added
- **Front & back matter constants** (`REQUIRED_FRONT_MATTER_SECTIONS`, `REQUIRED_BACK_MATTER_SECTIONS`) added
- **Validation tests** added and verified
- No API routes or database migrations added

### Module 3.2C Completed (Core Schema Cleanup & API Contract Preview)
- **Core schema exports** verified and cleaned up in `backend/app/schemas/__init__.py`
- **API contract preview document** (`backend/docs/api_contracts/core_book_contracts.md`) added
- **Sample payload document** (`backend/docs/api_contracts/sample_payloads.md`) added
- **Contract verification tests** (`backend/tests/test_core_schema_contracts.py`) added
- No API routes or database migrations added

### Module 3.3A Completed (RAG Source Schemas)
- **SourceDocument schemas** (`SourceDocumentCreate`, `SourceDocumentUpdate`, `SourceDocumentResponse`, `SourceDocumentListItem`) added
- **DocumentChunk schemas** (`DocumentChunkCreate`, `DocumentChunkUpdate`, `DocumentChunkResponse`, `DocumentChunkListItem`) added
- **Chunking request/response schemas** (`ChunkingRequest`, `ChunkingResponse`) added
- **Retrieval request/response schemas** (`RetrievalRequest`, `RetrievalResultItem`, `RetrievalResponse`) added
- **Validation tests** added and verified
- No RAG services, pgvector setup, or database migrations added

### Module 3.3B Completed (Memory Schemas)
- **FactRegistry schemas** (`FactRegistryCreate`, `FactRegistryUpdate`, `FactRegistryResponse`) added
- **ConceptBible schemas** (`ConceptBibleCreate`, `ConceptBibleUpdate`, `ConceptBibleResponse`) added
- **CharacterBible schemas** (`CharacterBibleCreate`, `CharacterBibleUpdate`, `CharacterBibleResponse`) added
- **CallbackIndex schemas** (`CallbackIndexCreate`, `CallbackIndexUpdate`, `CallbackIndexResponse`) added
- **ToneFingerprint schemas** (`ToneFingerprintCreate`, `ToneFingerprintUpdate`, `ToneFingerprintResponse`) added
- **DecisionLog schemas** (`DecisionLogCreate`, `DecisionLogUpdate`, `DecisionLogResponse`) added
- **Memory read/write envelope schemas** (`MemoryReadRequest`, `MemoryReadResponse`, `MemoryWriteRequest`, `MemoryWriteResponse`) added
- **Validation tests** added and verified
- No memory services, API routes, or database migrations added

### Module 3.4A Completed (Observability Schemas)
- **AgentTrace schemas** (`AgentTraceCreate`, `AgentTraceUpdate`, `AgentTraceResponse`) added
- **PromptLog schemas** (`PromptLogCreate`, `PromptLogUpdate`, `PromptLogResponse`) added
- **MemoryIOLog schemas** (`MemoryIOLogCreate`, `MemoryIOLogResponse`) added
- **TokenCostLedger schemas** (`TokenCostLedgerCreate`, `TokenCostLedgerUpdate`, `TokenCostLedgerResponse`) added
- **TraceBundleResponse schema** added
- **RunCostSummaryResponse schema** added
- **Validation tests** added and verified
- No observability services, API routes, or database migrations added

### Module 3.4B Completed (Eval + Export Schemas)
- **EvalResult schemas** (`EvalResultCreate`, `EvalResultUpdate`, `EvalResultResponse`) added
- **EvalMetricSummary & EvalReportResponse schemas** added
- **ExportFile schemas** (`ExportFileCreate`, `ExportFileUpdate`, `ExportFileResponse`, `ExportFileListItem`) added
- **ExportBundleResponse, ExportRequest, & ExportResponse schemas** added
- **Validation tests** added and verified
- No eval/export services, API routes, or database migrations added

### Module 3.5 Completed (Database Dashboard Setup via SQLAdmin)
- **sqladmin** added to requirements.txt and installed in the virtual environment.
- **ModelView configurations** created for all 18 database tables in `app/admin.py` with custom plurals, search, lists, and icons.
- **setup_admin** utility integrated in `app/main.py` create_app factory.
- **Verification tests** added under `tests/test_admin.py` and run successfully.

### Module 4.1A Completed (BookProject + BookRun Services & API Routes)
- **Services package** created under `backend/app/services/`
- **Service exceptions** (`ServiceError`, `NotFoundError`, `ValidationServiceError`, `ConflictError`) added to `app/services/exceptions.py`
- **BookProjectService** added to `app/services/book_service.py` with:
  - `create_book_project` — creates and persists a book project
  - `get_book_project` — fetch by id (raises `NotFoundError` if missing)
  - `list_book_projects` — paginated with status/tone/genre/search filters and sort
  - `update_book_project` — partial update (only set fields written)
  - `delete_book_project` — cascading delete
  - `mark_status` — updates status field
- **BookRunService** added to `app/services/run_service.py` with:
  - `create_run` — creates pending run, validates book exists
  - `get_run` — fetch by id (raises `NotFoundError` if missing)
  - `list_runs_for_book` — paginated with optional status filter, sorted latest-first
  - `update_run` — partial update
  - `mark_run_started` — sets status=running, started_at
  - `mark_run_completed` — sets status=completed, completed_at, clears current_agent
  - `mark_run_failed` — sets status=failed, completed_at, records error_message
  - `update_current_agent` — updates current_agent only
- **BookProject API routes** added in `app/api/routes_books.py` (prefix `/api/books`):
  - `POST /api/books` — create book (HTTP 201)
  - `GET /api/books` — paginated list with filters
  - `GET /api/books/{book_id}` — single book detail
  - `PATCH /api/books/{book_id}` — partial update
  - `DELETE /api/books/{book_id}` — delete with cascade
- **BookRun API routes** added in `app/api/routes_runs.py`:
  - `POST /api/books/{book_id}/runs` — create pending run
  - `GET /api/books/{book_id}/runs` — paginated run list
  - `GET /api/runs/{run_id}` — run detail
  - `PATCH /api/runs/{run_id}` — update run
  - `GET /api/runs/{run_id}/status` — monitoring envelope with progress_percentage
  - `POST /api/runs/{run_id}/start` — transition to running
  - `POST /api/runs/{run_id}/complete` — transition to completed
  - `POST /api/runs/{run_id}/fail` — transition to failed with error_message
- **Service tests** (24 tests) added in `tests/test_book_run_services.py`
- **API route tests** (21 tests) added in `tests/test_book_run_api.py`
- **conftest.py updated** — added `Base.metadata.create_all()` for API tests
- No agents, LangGraph, React UI, or database migrations added

### Module 4.1B Completed (Chapter + BookSection Services & API Routes)
- **ChapterService** added to `app/services/chapter_service.py` with:
  - `create_chapter` — validates book exists, raises `ConflictError` on duplicate `chapter_number`
  - `get_chapter` — fetch by id scoped to book (raises `NotFoundError` if missing)
  - `list_chapters` — paginated, filtered by status/tone/search, sorted by `chapter_number` asc
  - `update_chapter` — true partial update (only set fields written)
  - `delete_chapter` — permanent delete
  - `insert_chapter` — shifts existing chapters ≥ insertion point by +1, marks `repair_required=True` in `chapter_contract`
  - `reorder_chapters` — compacts gaps in `chapter_number` (1, 2, 3, …)
- **BookSectionService** added to `app/services/section_service.py` with:
  - `create_section` — path `book_id` overrides any `book_id` in payload
  - `get_section` — fetch by id scoped to book
  - `list_sections` — filtered by `section_type` / `status`, sorted by `sort_order` then `created_at`
  - `update_section` — partial update
  - `delete_section` — permanent delete
  - `create_default_structure` — idempotent creation of all required front/back matter sections
  - `reorder_sections` — compacts gaps in `sort_order` (0, 1, 2, …)
- **Shared error handler** added to `app/api/error_handlers.py`
- **Chapter API routes** added in `app/api/routes_chapters.py` (prefix `/api/books/{book_id}/chapters`):
  - `POST /api/books/{book_id}/chapters` — create chapter (HTTP 201, 409 on duplicate)
  - `GET /api/books/{book_id}/chapters` — paginated list
  - `GET /api/books/{book_id}/chapters/{chapter_id}` — chapter detail
  - `PATCH /api/books/{book_id}/chapters/{chapter_id}` — partial update
  - `DELETE /api/books/{book_id}/chapters/{chapter_id}` — delete
  - `POST /api/books/{book_id}/chapters/insert` — insert at position with shift + repair flag
  - `POST /api/books/{book_id}/chapters/reorder` — renumber sequentially
- **BookSection API routes** added in `app/api/routes_sections.py` (prefix `/api/books/{book_id}/sections`):
  - `POST /api/books/{book_id}/sections` — create section (HTTP 201)
  - `GET /api/books/{book_id}/sections` — list sections
  - `GET /api/books/{book_id}/sections/{section_id}` — section detail
  - `PATCH /api/books/{book_id}/sections/{section_id}` — partial update
  - `DELETE /api/books/{book_id}/sections/{section_id}` — delete
  - `POST /api/books/{book_id}/sections/defaults` — create all missing front/back matter sections (idempotent)
  - `POST /api/books/{book_id}/sections/reorder` — compact sort_order sequentially
- **Service tests** (26 tests) added in `tests/test_chapter_section_services.py`
- **API route tests** (22 tests) added in `tests/test_chapter_section_api.py`
- **API contracts doc** updated in `docs/api_contracts/core_book_contracts.md`
- No agents, LangGraph, React UI, or database migrations added
- Insert chapter does NOT run real repair workflow — only marks metadata with `repair_required=True`

---

### Module 4.2A Completed (RAG Source + Chunk Services and API Routes)
- **SourceDocumentService** added to `app/services/rag_service.py` with:
  - `create_source_document` — book scoped; path `book_id` is source of truth; verifies book exists
  - `get_source_document` — fetch by id (raises `NotFoundError` if missing)
  - `get_source_document_for_book` — fetch by id scoped to book
  - `list_source_documents` — paginated, newest-first; filters by `status`, `source_type`, `search`
  - `update_source_document` — true partial update
  - `delete_source_document` — permanent delete (cascades to chunks)
  - `mark_document_status` — update status field only
- **DocumentChunkService** added to `app/services/rag_service.py` with:
  - `create_chunk` — validates document exists; inherits `book_id` from parent; raises `ConflictError` on duplicate `chunk_index`
  - `get_chunk` — fetch by id
  - `get_chunk_for_document` — fetch by id scoped to document
  - `list_chunks` — paginated, sorted by `chunk_index` asc; filters by `document_id`, `book_id`, `embedding_status`, `search`
  - `update_chunk` — partial update (no vector fields)
  - `delete_chunk` — permanent delete
  - `mark_embedding_status` — update `embedding_status` + `embedding_model` metadata only; no vector stored
  - `simple_chunk_document_text` — deterministic character-window splitter; appends after max chunk_index; no LLM/embeddings
- **RAG API routes** added in `app/api/routes_rag.py`:
  - `POST /api/books/{book_id}/sources` — create source document (HTTP 201)
  - `GET /api/books/{book_id}/sources` — paginated list with filters
  - `GET /api/books/{book_id}/sources/{document_id}` — source detail
  - `PATCH /api/books/{book_id}/sources/{document_id}` — partial update
  - `DELETE /api/books/{book_id}/sources/{document_id}` — delete (cascades to chunks)
  - `PATCH /api/sources/{document_id}/status` — update status only
  - `POST /api/sources/{document_id}/chunks` — create chunk (HTTP 201, 409 on duplicate index)
  - `GET /api/sources/{document_id}/chunks` — paginated chunk list
  - `GET /api/sources/{document_id}/chunks/{chunk_id}` — chunk detail
  - `PATCH /api/sources/{document_id}/chunks/{chunk_id}` — partial update
  - `DELETE /api/sources/{document_id}/chunks/{chunk_id}` — delete
  - `PATCH /api/chunks/{chunk_id}/embedding-status` — update status + model metadata only
  - `POST /api/sources/{document_id}/chunk` — local character-window chunker (no LLM)
  - `POST /api/rag/retrieve` — placeholder ILIKE lexical retrieval (no pgvector, no embeddings)
- **Service tests** (23 tests) added in `tests/test_rag_services.py`
- **API route tests** (22 tests) added in `tests/test_rag_api.py`
- **API contracts doc** created at `docs/api_contracts/rag_contracts.md`
- No embeddings added; no pgvector added; no vector columns added
- No agents, LangGraph, React UI, or database migrations added
- Retrieval is placeholder lexical only — real vector search deferred to Module 6

---

### Module 4.2B Completed (Memory Services and API Routes)
- **MemoryService** added to `app/services/memory_service.py` with:
  - FactRegistry CRUD methods (`create_fact`, `get_fact`, `list_facts`, `update_fact`, `delete_fact`) sorted newest-first by created_at.
  - ConceptBible CRUD methods (`create_concept`, `get_concept`, `list_concepts`, `update_concept`, `delete_concept`) sorted alphabetically by concept name; enforces uniqueness.
  - CharacterBible CRUD methods (`create_character`, `get_character`, `list_characters`, `update_character`, `delete_character`) sorted alphabetically by character_name; enforces uniqueness.
  - CallbackIndex CRUD methods (`create_callback`, `get_callback`, `list_callbacks`, `update_callback`, `delete_callback`) sorted by source_chapter, target_chapter, then created_at.
  - ToneFingerprint CRUD methods (`create_tone_fingerprint`, `get_tone_fingerprint`, `list_tone_fingerprints`, `update_tone_fingerprint`, `delete_tone_fingerprint`) sorted newest-first by created_at.
  - DecisionLog CRUD methods (`create_decision`, `get_decision`, `list_decisions`, `update_decision`, `delete_decision`) supporting optional book scoping and newest-first sorting.
  - `read_memory` read envelope method supporting filtering by chapter_number and query string.
  - `write_memory` write envelope method supporting consistency validation of book_id and batch insertion.
- **Memory API routes** added in `app/api/routes_memory.py`:
  - `POST /api/books/{book_id}/memory/read` — batch read memories
  - `POST /api/books/{book_id}/memory/write` — batch write memories
  - Fact CRUD endpoints at `/api/books/{book_id}/memory/facts`
  - Concept CRUD endpoints at `/api/books/{book_id}/memory/concepts`
  - Character CRUD endpoints at `/api/books/{book_id}/memory/characters`
  - Callback CRUD endpoints at `/api/books/{book_id}/memory/callbacks`
  - Tone fingerprint CRUD endpoints at `/api/books/{book_id}/memory/tone-fingerprints`
  - Decision CRUD endpoints at `/api/books/{book_id}/memory/decisions` and global GET list at `/api/memory/decisions`
- **Service tests** (35 tests) added in `tests/test_memory_services.py`
- **API route tests** (10 tests covering 32 operations) added in `tests/test_memory_api.py`
- **API contracts doc** created at `docs/api_contracts/memory_contracts.md`
- No Memory Keeper Agent added; no automatic memory extraction added; no LangGraph/React UI added
- No pgvector added; no database migrations added

---

### Module 4.2C Completed (Observability Services and API Routes)
- **ObservabilityService** added to `app/services/observability_service.py` with:
  - AgentTrace CRUD methods (`create_agent_trace`, `get_agent_trace`, `get_agent_trace_for_run`, `list_agent_traces`, `update_agent_trace`, `delete_agent_trace`) sorted ascending by `created_at`.
  - PromptLog CRUD methods (`create_prompt_log`, `get_prompt_log`, `get_prompt_log_for_run`, `list_prompt_logs`, `update_prompt_log`, `delete_prompt_log`) sorted newest-first by `created_at` with ILIKE search capability.
  - MemoryIOLog CRUD methods (`create_memory_io_log`, `get_memory_io_log`, `list_memory_io_logs`, `delete_memory_io_log`) sorted newest-first by `created_at`.
  - TokenCostLedger CRUD methods (`create_token_cost`, `get_token_cost`, `list_token_costs`, `update_token_cost`, `delete_token_cost`) sorted newest-first by `created_at` with auto-computation of `total_tokens = input_tokens + output_tokens`.
  - `get_trace_bundle` trace bundle compiler to export all observability rows for a run execution.
  - `get_run_cost_summary` cost summary aggregator grouped by model breakdown.
- **Observability API routes** added in `app/api/routes_observability.py`:
  - POST/GET traces scoped to `/api/runs/{run_id}/observability/traces`
  - GET/PATCH/DELETE single trace scoped to `/api/observability/traces/{trace_id}`
  - POST/GET prompts scoped to `/api/runs/{run_id}/observability/prompts`
  - GET/PATCH/DELETE single prompt scoped to `/api/observability/prompts/{prompt_log_id}`
  - POST/GET memory operations scoped to `/api/runs/{run_id}/observability/memory-io`
  - GET/DELETE single memory operation scoped to `/api/observability/memory-io/{log_id}`
  - POST/GET token cost entries scoped to `/api/runs/{run_id}/observability/token-costs`
  - GET/PATCH/DELETE single token cost scoped to `/api/observability/token-costs/{cost_id}`
  - GET `/api/runs/{run_id}/observability/trace-bundle` — trace bundle compilation
  - GET `/api/runs/{run_id}/observability/cost-summary` — cost summary aggregated grouped by model
- **Service tests** (32 tests) added in `tests/test_observability_services.py`
- **API route tests** (10 tests covering 26 operations) added in `tests/test_observability_api.py`
- **API contracts doc** created at `docs/api_contracts/observability_contracts.md`
- **No agents, LangGraph, React UI, or database migrations** added.
- **No vector columns or pgvector** added.
- **Thin route layer** that calls services directly and handles errors cleanly via the shared route error mapper.

---

### Module 4.2D Completed (Eval + Export Services and API Routes)
- **EvalService** added to `app/services/eval_service.py` with:
  - EvalResult CRUD methods (`create_eval_result`, `get_eval_result`, `get_eval_result_for_book`, `list_eval_results`, `update_eval_result`, `delete_eval_result`) sorted newest-first by `created_at`.
  - `get_eval_report` report compiler that aggregates and summarizes stored evaluation result rows, calculating score stats and overall statuses.
- **ExportService** added to `app/services/export_service.py` with:
  - ExportFile CRUD methods (`create_export_file`, `get_export_file`, `get_export_file_for_book`, `list_export_files`, `update_export_file`, `delete_export_file`) sorted newest-first.
  - `request_exports` method that maps export requests into virtual placeholder DB records (`pending://` URI format).
  - `get_export_bundle` method compiling all ready/failed/total files generated for a book run.
- **Eval/Export API routes** added in `app/api/routes_eval_export.py`:
  - POST/GET evals scoped to `/api/books/{book_id}/evals`
  - GET/PATCH/DELETE single eval scoped to `/api/books/{book_id}/evals/{eval_id}`
  - GET `/api/books/{book_id}/eval-report` — compiled evaluation reports
  - POST run-scoped evals scoped to `/api/runs/{run_id}/evals`
  - POST/GET exports scoped to `/api/books/{book_id}/exports`
  - GET/PATCH/DELETE single export scoped to `/api/books/{book_id}/exports/{export_id}`
  - POST `/api/books/{book_id}/exports/request` — request format creation (placeholders only)
  - GET `/api/books/{book_id}/exports/bundle` — compiled exports bundle overview
  - GET `/api/runs/{run_id}/exports` — list exports scoped to run execution
- **Service tests** (23 tests) added in `tests/test_eval_export_services.py`
- **API route tests** (7 tests covering 20 operations) added in `tests/test_eval_export_api.py`
- **API contracts doc** created at `docs/api_contracts/eval_export_contracts.md`
- **No real eval runner, physical files on disk, or agents/LangGraph/UI** added.
- **No database migrations or pgvector vector columns** added.
- **Thin route layer** calling services directly and utilizing route ordering to avoid Starlette UUID pattern conflicts.

---

## Module 3 Completed: Pydantic Schemas & DB Admin Dashboard

- **Schema Foundation Completed**: Base schemas, shared enums, generic pagination/sorting, health endpoints, and standardized error schemas implemented.
- **Book/Run Schemas Completed**: Inputs, updates, responses, and list structures implemented.
- **Chapter/Section Schemas Completed**: Planning contracts, insert layouts, and front/back matter specifications defined.
- **RAG Schemas Completed**: Source document, chunk, chunking request, and retrieval schemas implemented.
- **Memory Schemas Completed**: Concept bible, fact registry, character bible, continuity callback index, tone fingerprint, and decision log schemas implemented.
- **Observability Schemas Completed**: Trace logs, prompt logging, memory I/O logs, token cost ledger, and run summary stats implemented.
- **Eval/Export Schemas Completed**: Eval results, report summaries, export file outputs, requests, and bundle structures implemented.
- **Final Schema Verification Completed**: Package exports, required sections, payload validation, and dependency-free checks implemented.
- **No database migrations** were created during Module 3.
- **No API routes or services** were implemented yet.
- **Module 4** started API route/service implementation.

## Database & Schema Module Status

* **Module 2 Completion**: Module 2 has completed the database foundation.
* **Relational Tables**: All 18 relational tables are created and fully migrated.
* **Module 3 Completion**: Module 3 has completed the Pydantic schema validation layer and the SQLAdmin database administration dashboard at `http://localhost:8000/admin`. All 120+ schema classes and constants are exported, fully tested, and verified. All 18 relational tables are registered in the admin dashboard.
* **Postponed pgvector**: In accordance with DEC-011, `pgvector` configuration and embedding columns are postponed to Module 6.
* **Next Phase**: Module 4 (API Routes & Services).

* **Agent System**: No agent orchestrations or workflows exist yet.

### Useful Database & Test Commands

* **View Current Migration Revision**:
  ```powershell
  alembic current
  ```
* **Apply Outstanding Migrations**:
  ```powershell
  alembic upgrade head
  ```
* **Inspect Database Integrity & Tables**:
  ```powershell
  python scripts/check_db.py
  ```
* **Run Test Suites**:
  ```powershell
  pytest
  ```

---

## Database Migrations (Alembic)

Database schemas are versioned and managed using **Alembic**.

### How to Create a New Migration
Run this command from the `backend/` directory to generate a new migration script based on detection of changes in `app/models/`:
```powershell
alembic revision --autogenerate -m "description of changes"
```
The migration script is created under `backend/alembic/versions/`.

### How to Run Migrations
Apply all pending database migrations to the configured database:
```powershell
alembic upgrade head
```

### How to Rollback a Migration
Rollback the last migration:
```powershell
alembic downgrade -1
```

---

## Folder Structure

```
backend/
├── alembic/                # Migration environment and version files
│   ├── env.py              # Script run when Alembic env is invoked
│   ├── script.py.mako      # Template for migrations
│   └── versions/           # Folder containing migration revisions
├── app/
│   ├── api/                # FastAPI routing layers
│   ├── models/             # SQLAlchemy ORM models package
│   │   ├── __init__.py     # Module level declarations
│   │   └── base.py         # Custom types and common mixins (GUID, Timestamps)
│   ├── config.py           # Configuration management
│   ├── database.py         # Database engine and dependency session injections
│   └── main.py             # App instantiation and middleware
├── tests/                  # Test suite
└── alembic.ini             # Alembic system configuration settings
```
