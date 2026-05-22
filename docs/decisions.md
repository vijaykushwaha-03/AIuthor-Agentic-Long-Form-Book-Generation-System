# Engineering Decisions Log

This file documents all non-obvious engineering choices made during the AIuthor build. Each entry includes the decision, the rationale, and the alternatives considered.

---

## DEC-001: Sync SQLAlchemy for Module 1

**Decision**: Use synchronous `create_engine` and `SessionLocal` in Module 1.

**Rationale**: Async SQLAlchemy adds complexity (separate session maker, async context managers, different dependency injection pattern). For Module 1 we only need a health check DB ping. Keeping sync here lets us validate the wiring without async overhead. We will migrate to `AsyncSession` in Module 2 when real queries are introduced.

**Alternatives considered**: `asyncpg` + `SQLAlchemy[asyncio]` — deferred to Module 2.

---

## DEC-002: Pydantic Settings for Config

**Decision**: Use `pydantic-settings` `BaseSettings` as the single config layer.

**Rationale**: Pydantic Settings provides automatic `.env` file loading, type coercion, and validation at startup. Any misconfigured environment variable (wrong type, missing required value) raises an error immediately on boot rather than causing a silent runtime failure deep in request handling.

**Alternatives considered**: `python-decouple`, raw `os.environ` — rejected because they lack type validation.

---

## DEC-003: App Factory Pattern (`create_app()`)

**Decision**: Export a `create_app()` function from `main.py` rather than a module-level `app` instance.

**Rationale**: Factory pattern allows tests to create isolated app instances with different config (e.g., test DB URL). The Uvicorn/Gunicorn entrypoint calls `create_app()` at startup — this is the same approach used by Flask and FastAPI best-practice guides.

**Alternatives considered**: Module-level `app = FastAPI()` — rejected because it makes testing and config injection harder.

---

## DEC-004: SQLite In-Memory DB for Tests

**Decision**: The pytest `conftest.py` overrides the DB dependency with an in-memory SQLite engine.

**Rationale**: This means the test suite runs without a running Postgres instance. CI/CD environments do not need Docker for basic unit and health tests. Integration tests that require pgvector will use a dedicated test Postgres container (added in Module 6).

**Alternatives considered**: pytest-postgresql, testcontainers — deferred to Module 6 when pgvector queries begin.

---

## DEC-005: `/health` at Root, `/api/version` Under Prefix

**Decision**: Health endpoint is `GET /health` (no `/api/` prefix). Version is `GET /api/version`.

**Rationale**: Load balancers and container orchestrators (Kubernetes liveness probes, AWS ALB health checks) typically probe a flat `/health` URL without any path prefix. Keeping it at root makes zero-config probe setup possible. Version is an API metadata endpoint, so it belongs under `/api/`.

---

## DEC-006: LangGraph for Orchestration (not raw Celery or asyncio tasks)

**Decision**: Use LangGraph as the agent orchestration framework.

**Rationale**: LangGraph provides a typed state graph with conditional edges, built-in retry logic, checkpointing, and human-in-the-loop support. These are all required by the spec (repair loops, chapter insertion re-runs). Building equivalent functionality on raw asyncio tasks or Celery would require significant custom code.

**Alternatives considered**: Celery, raw asyncio, Prefect — all lack the native LLM agent-loop abstractions.

---

## DEC-007: Prompts as Markdown Files Under `prompts/`

**Decision**: Every agent prompt is a `.md` file in `backend/prompts/`. No prompt strings are hardcoded in Python.

**Rationale**: Prompts are part of the product. They need to be version-controlled, diff-able, and auditable. Storing them as `.md` files means a PM or prompt engineer can edit them without touching Python code. The prompt registry module loads them at startup.

---

## DEC-008: Token/Cost Ledger as a DB Table

**Decision**: Every LLM call logs `prompt_tokens`, `completion_tokens`, `model`, `estimated_cost_usd` into a `token_cost_ledger` DB table.

**Rationale**: Cost visibility is mandatory in production. Logging to DB (not just stdout) means costs can be queried per-book, per-run, and per-agent, and exposed in the React UI.

---

## DEC-009: Chapter Insertion Triggers a Repair Run

**Decision**: Inserting a new chapter does not do an in-place edit. It triggers a new LangGraph repair run that re-runs the Planner (TOC repair), re-indexes callbacks, and regenerates the glossary.

**Rationale**: In-place surgery on an already-generated book risks silent inconsistencies. A repair run goes through the same pipeline, preserving all observability (traces, prompt logs) and producing a new set of exports.

---

## DEC-010: Backend-First Delivery

**Decision**: All agent logic, memory, RAG, evals, and exports are implemented and tested before the React UI is built.

**Rationale**: The primary assessment value is in the agent graph, memory schema, prompt dossier, traceability, evals, and self-healing logic. The UI is a demonstration layer. Building the backend first means the UI has real APIs to connect to and does not require any mock data.
