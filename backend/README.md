# AIuthor Backend — Developer Reference

This directory contains the FastAPI backend code, database configurations, migrations, prompts, and testing suites.

## Project Progress Status

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

---

## Module 3 Completed: Pydantic Schemas

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
- **Module 4** will start API route/service implementation.

## Database & Schema Module Status

* **Module 2 Completion**: Module 2 has completed the database foundation.
* **Relational Tables**: All 18 relational tables are created and fully migrated.
* **Module 3 Completion**: Module 3 has completed the Pydantic schema validation layer. All 120+ schema classes and constants are exported, fully tested, and verified.
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
