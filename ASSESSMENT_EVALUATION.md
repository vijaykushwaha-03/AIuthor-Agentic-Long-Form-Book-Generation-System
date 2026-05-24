# AIuthor — Assessment Alignment Evaluation Report

**Evaluated against:** AIuthor AI Engineer Assessment v1.1 (2-pager)  
**Evaluation date:** 2026-05-24  
**System state:** Backend complete, Frontend not started  

---

## Overall Score: 71 / 100

| Domain | Max | Score | Status |
|--------|-----|-------|--------|
| Architecture & Stack | 15 | 13 | ✅ Strong |
| Agent Pipeline | 20 | 16 | ✅ Good |
| Memory System | 15 | 13 | ✅ Strong |
| RAG Pipeline | 10 | 8 | ✅ Good |
| Observability | 10 | 8 | ✅ Good |
| Self-Healing (Test D) | 10 | 8 | ✅ Good |
| Evals / Quality Gates | 10 | 5 | ⚠️ Partial |
| Frontend | 10 | 0 | ❌ Missing |

---

## 1. Architecture & Stack — 13/15 ✅

### What the assessment requires
- FastAPI + Pydantic v2 backend
- PostgreSQL + pgvector for persistent memory and RAG
- LangGraph for stateful multi-agent orchestration
- python-docx + LibreOffice for DOCX/PDF export
- React + Vite + Tailwind frontend
- Docker Compose for full local stack

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| FastAPI + Pydantic v2 | ✅ Done | `fastapi==0.111.0`, `pydantic==2.7.1` |
| PostgreSQL + pgvector | ✅ Done | pgvector confirmed installed and operational |
| LangGraph orchestration | ✅ Done | `langgraph==1.2.1`, both pipelines compiled |
| python-docx export | ✅ Done | DOCX generation working |
| LibreOffice PDF export | ⚠️ Conditional | Works only if LibreOffice installed locally |
| React + Vite + Tailwind | ❌ Missing | Not started |
| Docker Compose | ⚠️ Partial | `docker-compose.yml` exists but not the primary dev path |
| Alembic migrations | ✅ Done | 9 migration files present |

**Deductions:** -2 for no frontend, no Docker-first dev workflow.

---

## 2. Agent Pipeline — 16/20 ✅

### What the assessment requires
8 distinct agents with strict Pydantic I/O contracts, no giant prompts, each agent doing one job:
- Planner → Researcher → Writer → Humanizer → Editor → Fact Checker → Memory Keeper → Assembler

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| All 8 agents exist | ✅ Done | `app/agents/` — all 8 classes |
| BaseAgent with LLM + mock mode | ✅ Done | `run()` and `run_mock()` on every agent |
| Strict Pydantic I/O schemas | ✅ Done | `AgentInput`, `AgentOutput` schemas |
| Prompt registry (markdown files) | ✅ Done | All 8 `.md` files in `prompts/agents/` |
| LangGraph 8-node `full_agent_pipeline` | ✅ Done | `graph.py` — compiled and runnable |
| LangGraph 5-node `mini_book_pipeline` | ✅ Done | Simpler pipeline also available |
| Mock execution mode | ✅ Done | `MockLLMProvider` — no API keys needed |
| Real execution mode (Gemini) | ✅ Done | Gated by `ENABLE_REAL_WORKFLOW_TEST_API` |
| Conditional edges / retry loops | ❌ Missing | All edges are linear — no branching on failure |
| Fact-check failure → re-run Writer | ❌ Missing | Fact checker flags but does not loop back |
| Agent-level token tracking | ✅ Done | `TokenCostLedger` table, per-agent logging |

**Deductions:** -4 for no conditional edges and no repair loops inside the graph. The assessment specifically calls out "routing to repair on fact-check failure" as a LangGraph requirement. Currently the graph is sequential only.

---

## 3. Memory System — 13/15 ✅

### What the assessment requires
Persistent memory outside the LLM context window using PostgreSQL tables:
- Fact Registry
- Concept Bible
- Character Bible
- Callback Index
- Tone Fingerprint
- Decision Log

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| `FactRegistry` table + service | ✅ Done | Full CRUD + extraction service |
| `ConceptBible` table + service | ✅ Done | Unique constraint per book+concept |
| `CharacterBible` table + service | ✅ Done | For fiction/narrative genres |
| `CallbackIndex` table + service | ✅ Done | Cross-chapter reference tracking |
| `ToneFingerprint` table + service | ✅ Done | Banned phrases, lexical rules |
| `DecisionLog` table + service | ✅ Done | Engineering + generation decisions |
| `MemoryExtractionService` | ✅ Done | Extracts from chapter text via LLM |
| `ContinuityPackService` | ✅ Done | Builds markdown continuity pack for agents |
| `MemoryIOLog` observability | ✅ Done | Every memory read/write logged |
| Memory API endpoints | ✅ Done | Full REST API for all memory tables |

**Deductions:** -2 for memory extraction relying on LLM JSON parsing which can fail silently if the LLM returns malformed JSON. No fallback regex/heuristic extraction exists.

---

## 4. RAG Pipeline — 8/10 ✅

### What the assessment requires
- Document ingestion and chunking
- Embedding via pgvector
- Cosine similarity retrieval
- Evidence pack building for agents

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| `SourceDocument` + `DocumentChunk` models | ✅ Done | With pgvector `Vector(768)` column |
| Gemini embedding provider | ✅ Done | Fixed to `gemini-embedding-001`, 768-dim |
| OpenAI embedding provider | ✅ Done | `text-embedding-3-small` |
| Mock embedding provider | ✅ Done | Deterministic hash-based vectors |
| `ChunkEmbeddingService` | ✅ Done | Batch embedding with dimension validation |
| `SemanticRetrievalService` | ✅ Done | pgvector native `<=>` operator + Python fallback |
| `HybridRetrievalService` | ✅ Done | Vector + keyword combined ranking |
| `ContextPackService` | ✅ Done | Builds RAG context pack per chapter |
| pgvector ANN index (HNSW/IVFFlat) | ❌ Missing | No index created on the embedding column — full scan only |
| Document chunking API | ✅ Done | `routes_rag.py` — chunk + embed endpoints |

**Deductions:** -2 for no vector index. On large document sets this will be very slow. An HNSW or IVFFlat index on `document_chunks.embedding` is needed for production.

---

## 5. Observability — 8/10 ✅

### What the assessment requires
- `agent_traces`: execution states and summaries
- `prompt_logs`: exact rendered prompts and payloads
- `memory_io_logs`: every memory read/write
- `token_cost_ledger`: token usage and estimated costs per agent

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| `AgentTrace` model + service | ✅ Done | Per-agent execution trace |
| `PromptLog` model + service | ✅ Done | Exact system + user prompt logged |
| `MemoryIOLog` model + service | ✅ Done | Every memory operation logged |
| `TokenCostLedger` model + service | ✅ Done | Tokens + estimated USD cost |
| `WorkflowObservabilityService` | ✅ Done | Aggregates traces per workflow run |
| Observability API endpoints | ✅ Done | Full REST API |
| Trace bundle packaging | ✅ Done | `DeliveryBundleService` packages traces |
| Real-time streaming / SSE | ❌ Missing | No live progress streaming to client |
| Cost estimation formula | ⚠️ Partial | Cost stored but pricing table may be outdated |

**Deductions:** -2 for no real-time streaming. The assessment implies a "Run Monitor UI" that shows live agent progress — this requires SSE or WebSocket, neither of which is implemented.

---

## 6. Self-Healing Chapter Insertion (Test D) — 8/10 ✅

### What the assessment requires
Inserting a new chapter must automatically:
1. Repair the Table of Contents
2. Update callback numbers
3. Regenerate the glossary
4. Produce a trace bundle of the repair run

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| Chapter insertion at any position | ✅ Done | `insert_at_chapter_number` param |
| Chapter renumbering | ✅ Done | All subsequent chapters shifted |
| TOC repair | ✅ Done | `BookSection` with `section_type=toc` rebuilt |
| Callback index repair | ✅ Done | `source_chapter` and `target_chapter` shifted |
| Concept Bible repair | ✅ Done | `first_chapter` and `appears_in_chapters` shifted |
| Back matter section repair | ✅ Done | Glossary, appendix, index metadata updated |
| Repair items logged | ✅ Done | `StructureRepairItem` per repair action |
| Trace bundle on repair run | ✅ Done | Full agent trace + prompt log |
| Glossary content regeneration via LLM | ❌ Missing | Metadata updated but glossary text not re-generated |
| Independent repair sub-system isolation | ✅ Done | Each repair in its own try/except |

**Deductions:** -2 for glossary text not being regenerated. The assessment expects the glossary content itself to be rebuilt, not just its metadata updated.

---

## 7. Evals / Quality Gates — 5/10 ⚠️

### What the assessment requires
Automated programmatic quality gates scoring:
- Structure (chapter sequence, TOC completeness)
- Tone consistency (AI tells detection)
- Fact grounding (claims vs. citations)
- Callback integrity
- Insertion repair verification

### What is built
| Requirement | Status | Notes |
|-------------|--------|-------|
| `EvaluationReportService` | ✅ Done | Structural checks, export checks, trace checks |
| `EvalResult` model | ✅ Done | Persisted per book/run |
| Chapter sequence check | ✅ Done | Detects gaps and duplicates |
| Export file existence check | ✅ Done | Verifies DOCX/PDF generated |
| Trace coverage check | ✅ Done | Verifies agent traces exist |
| AI tells detection | ❌ Missing | No heuristic or LLM-based AI tell scorer |
| Tone consistency scoring | ❌ Missing | No tone fingerprint comparison |
| Fact grounding score | ❌ Missing | No claim-vs-citation coverage metric |
| Callback integrity check | ❌ Missing | No cross-chapter callback validation |
| Insertion repair verification | ⚠️ Partial | Repair items logged but not scored |
| Numeric quality scores (0–100) | ❌ Missing | Report is pass/warning/fail, not scored |

**Deductions:** -5 for missing the core quality scoring. The assessment specifically calls out AI tells, tone, fact grounding, and callback evals as mandatory quality gates. What exists is structural/metadata checking only.

---

## 8. Frontend — 0/10 ❌

### What the assessment requires
- React + Vite + Tailwind setup
- New Book Brief UI (form → launch run)
- Run Monitor UI (live agent timeline)
- Book Preview UI (chapters + insert chapter)
- Observability & Export UI (memory, traces, eval reports, download buttons)

### What is built
Nothing. The frontend directory does not exist. This is the largest single gap.

---

## 9. Assessment Test Cases (A–D)

The assessment defines 4 mandatory test scenarios:

| Test | Description | Status |
|------|-------------|--------|
| **A** | 10-chapter technical nonfiction (finance/AI guide) with full pipeline | ⚠️ API exists, not run end-to-end with real LLM |
| **B** | Fiction/creative with character memory and tone control | ⚠️ API exists, not run end-to-end |
| **C** | Dense knowledge with RAG citations and bibliography | ⚠️ API exists, RAG pipeline ready |
| **D** | Chapter insertion self-healing with trace bundle | ✅ Fully implemented and documented |

Test D is the most complete. Tests A–C have all the API infrastructure but have not been executed end-to-end with real Gemini to produce actual output artifacts.

---

## What Needs to Be Added (Priority Order)

### P1 — Critical (blocks assessment score)

1. **Frontend (React + Vite + Tailwind)**
   - New Book Brief form
   - Run Monitor with polling or SSE
   - Book Preview with chapter insert UI
   - Export download buttons
   - Memory/Traces/Eval dashboard

2. **LangGraph conditional edges**
   - Fact-check failure → route back to Writer node
   - Quality gate threshold → conditional END vs retry
   - This is explicitly called out in the assessment as a LangGraph requirement

3. **AI tells + tone eval scorer**
   - Heuristic list of AI phrases ("It is worth noting", "In conclusion", "Delve into", etc.)
   - Tone fingerprint comparison between chapters
   - Numeric score 0–100

4. **Fact grounding eval**
   - Count claims in chapter text
   - Count claims with a matching `chunk_id` in `FactRegistry`
   - Grounding score = matched / total

### P2 — Important (improves score significantly)

5. **pgvector HNSW index**
   - Add Alembic migration: `CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops)`
   - Required for any real-scale document set

6. **Glossary text regeneration on chapter insert**
   - After repair, re-run the Assembler agent on the glossary section
   - Currently only metadata is updated

7. **Run end-to-end Test A with real Gemini**
   - Execute the full 10-chapter pipeline
   - Produce actual DOCX/PDF artifacts
   - These are the deliverables the assessment evaluator will look at

8. **SSE / WebSocket for live run progress**
   - `GET /api/books/{id}/runs/{run_id}/stream` — Server-Sent Events
   - Required for the Run Monitor UI

### P3 — Nice to have

9. **Callback integrity eval**
   - Verify every `CallbackIndex` record's `source_chapter` and `target_chapter` are valid
   - Flag orphaned callbacks after chapter operations

10. **Docker Compose as primary dev path**
    - Currently Docker exists but local Postgres is the documented path
    - Assessment likely expects `docker compose up` to start everything

11. **Async background execution**
    - Currently all pipeline runs are synchronous (blocks the HTTP request)
    - For 10-chapter books this will timeout
    - Needs Celery + Redis or FastAPI BackgroundTasks + polling

---

## What Should Be Removed

| Item | Reason |
|------|--------|
| `backend/scratch/` directory | Scratch files should not be in the repo |
| `sqladmin` admin dashboard | Not in the assessment requirements, adds dependency weight |
| `routes_backend_qa.py` self-assessment endpoint | Internal tooling, not an assessment deliverable |
| `e2e_dry_run_service.py` | Redundant with actual test runs; adds complexity |

---

## Summary

The backend is **well-engineered and substantially complete**. The data models, agent pipeline, memory system, RAG pipeline, observability, and self-healing are all production-quality implementations. The main gaps are:

1. **No frontend** — the assessment requires a working UI
2. **No conditional LangGraph edges** — the graph is linear, not adaptive
3. **Weak evals** — structural checks only, no AI tells / tone / fact grounding scores
4. **No end-to-end artifact** — Tests A–C have not been run to produce actual book output

Fixing P1 items (frontend + conditional edges + eval scorers + one real end-to-end run) would bring the score from **71 to approximately 88–92**.
