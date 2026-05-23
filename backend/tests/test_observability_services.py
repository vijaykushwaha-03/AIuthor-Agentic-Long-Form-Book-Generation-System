"""
AIuthor Backend Tests — ObservabilityService unit tests.

Tests use a per-test transaction rollback for isolation against in-memory SQLite.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from uuid import uuid4, UUID

from app.database import Base
import app.models  # noqa: F401

from app.services import (
    BookProjectService,
    BookRunService,
    ObservabilityService,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)
from app.schemas import (
    BookProjectCreate,
    BookRunCreate,
    AgentTraceCreate,
    AgentTraceUpdate,
    PromptLogCreate,
    PromptLogUpdate,
    MemoryIOLogCreate,
    TokenCostLedgerCreate,
    TokenCostLedgerUpdate,
)
from app.schemas.enums import TonePreset, AgentName, AgentStatus, MemoryOperation

# ── In-memory test engine ─────────────────────────────────────────────────────

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_ENGINE)
_Session = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    connection = _ENGINE.connect()
    transaction = connection.begin()
    session = _Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_book(db):
    return BookProjectService(db).create_book_project(
        BookProjectCreate(
            topic="Observability Test",
            reader_profile="Testers",
            genre="Fiction",
            tone=TonePreset.CONVERSATIONAL,
            target_chapters=3,
        )
    )


def _make_run(db, book_id):
    return BookRunService(db).create_run(
        BookRunCreate(
            book_id=book_id,
            run_metadata={"environment": "test"},
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# AgentTrace Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentTraceService:

    def test_create_agent_trace_creates_trace(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        trace = svc.create_agent_trace(
            AgentTraceCreate(
                run_id=run.id,
                book_id=book.id,
                agent_name=AgentName.PLANNER,
                status=AgentStatus.STARTED,
                input_summary="Outline request input summary",
                started_at=datetime.utcnow(),
            )
        )
        assert trace.id is not None
        assert trace.run_id == run.id
        assert trace.agent_name == "planner"
        assert trace.status == "started"

    def test_get_agent_trace_returns_trace(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        created = svc.create_agent_trace(
            AgentTraceCreate(run_id=run.id, agent_name="test_agent", status="started")
        )
        fetched = svc.get_agent_trace(created.id)
        assert fetched.id == created.id
        assert fetched.agent_name == "test_agent"

    def test_get_agent_trace_for_run_returns_trace(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        created = svc.create_agent_trace(
            AgentTraceCreate(run_id=run.id, agent_name="scoped_agent", status="started")
        )
        fetched = svc.get_agent_trace_for_run(run.id, created.id)
        assert fetched.id == created.id

    def test_get_agent_trace_for_run_raises_not_found(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        created = svc.create_agent_trace(
            AgentTraceCreate(run_id=run.id, agent_name="scoped_agent", status="started")
        )
        with pytest.raises(NotFoundError):
            svc.get_agent_trace_for_run(uuid4(), created.id)

    def test_list_agent_traces_filters_by_agent_name(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent_a", status="started"))
        svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent_b", status="started"))

        items, total = svc.list_agent_traces(run_id=run.id, agent_name="agent_a")
        assert total == 1
        assert items[0].agent_name == "agent_a"

    def test_list_agent_traces_filters_by_status(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent", status="started"))
        svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent", status="completed"))

        items, total = svc.list_agent_traces(run_id=run.id, status="completed")
        assert total == 1
        assert items[0].status == "completed"

    def test_update_agent_trace_updates_status(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        trace = svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent", status="started"))

        updated = svc.update_agent_trace(
            trace.id, AgentTraceUpdate(status="completed", output_summary="Outline generated successfully.")
        )
        assert updated.status == "completed"
        assert updated.output_summary == "Outline generated successfully."

    def test_delete_agent_trace_deletes_trace(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        trace = svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent", status="started"))

        res = svc.delete_agent_trace(trace.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_agent_trace(trace.id)

    def test_create_agent_trace_for_missing_run_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.create_agent_trace(AgentTraceCreate(run_id=uuid4(), agent_name="agent", status="started"))
        assert exc.value.code == "run_not_found"


# ══════════════════════════════════════════════════════════════════════════════
# PromptLog Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptLogService:

    def test_create_prompt_log_creates_prompt_log(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        log = svc.create_prompt_log(
            PromptLogCreate(
                run_id=run.id,
                book_id=book.id,
                agent_name=AgentName.RESEARCHER,
                model_name="gpt-4o",
                prompt_name="research_gather",
                prompt_text="Explain quantum gravity in simple terms.",
                input_payload={"topic": "quantum gravity"},
            )
        )
        assert log.id is not None
        assert log.prompt_text == "Explain quantum gravity in simple terms."

    def test_list_prompt_logs_filters_by_model_name(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", model_name="gpt-4", prompt_text="Prompt 1"))
        svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", model_name="claude-3", prompt_text="Prompt 2"))

        items, total = svc.list_prompt_logs(run_id=run.id, model_name="gpt-4")
        assert total == 1
        assert items[0].model_name == "gpt-4"

    def test_list_prompt_logs_search_finds_prompt_text(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", prompt_text="Write a story about a dragon."))
        svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", prompt_text="Factual QA on history."))

        items, total = svc.list_prompt_logs(run_id=run.id, search="dragon")
        assert total == 1
        assert "dragon" in items[0].prompt_text

    def test_update_prompt_log_updates_output_payload(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        log = svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", prompt_text="Prompt text"))

        updated = svc.update_prompt_log(log.id, PromptLogUpdate(output_payload={"response": "Story about dragon"}))
        assert updated.output_payload == {"response": "Story about dragon"}

    def test_delete_prompt_log_deletes_prompt_log(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        log = svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", prompt_text="Prompt text"))

        res = svc.delete_prompt_log(log.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_prompt_log(log.id)

    def test_create_prompt_log_for_missing_run_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError):
            svc.create_prompt_log(PromptLogCreate(run_id=uuid4(), agent_name="agent", prompt_text="Prompt text"))


# ══════════════════════════════════════════════════════════════════════════════
# MemoryIOLog Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMemoryIOLogService:

    def test_create_memory_io_log_creates_log(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        log = svc.create_memory_io_log(
            MemoryIOLogCreate(
                run_id=run.id,
                book_id=book.id,
                agent_name=AgentName.MEMORY_KEEPER,
                operation=MemoryOperation.WRITE,
                memory_type="concept_bible",
                payload={"concept": "Warp Core", "definition": "Anti-matter drive."},
            )
        )
        assert log.id is not None
        assert log.memory_type == "concept_bible"
        assert log.operation == "write"

    def test_list_memory_io_logs_filters_by_operation(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_memory_io_log(MemoryIOLogCreate(run_id=run.id, operation="read", memory_type="concept"))
        svc.create_memory_io_log(MemoryIOLogCreate(run_id=run.id, operation="write", memory_type="concept"))

        items, total = svc.list_memory_io_logs(run_id=run.id, operation="read")
        assert total == 1
        assert items[0].operation == "read"

    def test_list_memory_io_logs_filters_by_memory_type(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_memory_io_log(MemoryIOLogCreate(run_id=run.id, operation="read", memory_type="concept_bible"))
        svc.create_memory_io_log(MemoryIOLogCreate(run_id=run.id, operation="read", memory_type="character_bible"))

        items, total = svc.list_memory_io_logs(run_id=run.id, memory_type="character_bible")
        assert total == 1
        assert items[0].memory_type == "character_bible"

    def test_delete_memory_io_log_deletes_log(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        log = svc.create_memory_io_log(MemoryIOLogCreate(run_id=run.id, operation="read", memory_type="concept"))

        res = svc.delete_memory_io_log(log.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_memory_io_log(log.id)

    def test_create_memory_io_log_for_missing_run_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError):
            svc.create_memory_io_log(MemoryIOLogCreate(run_id=uuid4(), operation="read", memory_type="concept"))


# ══════════════════════════════════════════════════════════════════════════════
# TokenCostLedger Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenCostLedgerService:

    def test_create_token_cost_computes_total_tokens_when_missing(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        cost = svc.create_token_cost(
            TokenCostLedgerCreate(
                run_id=run.id,
                book_id=book.id,
                agent_name=AgentName.WRITER,
                model_name="gpt-4o",
                input_tokens=1500,
                output_tokens=500,
                estimated_cost=Decimal("0.015"),
            )
        )
        assert cost.id is not None
        assert cost.total_tokens == 2000

    def test_list_token_costs_filters_by_model_name(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        svc.create_token_cost(TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o"))
        svc.create_token_cost(TokenCostLedgerCreate(run_id=run.id, model_name="claude-3-5"))

        items, total = svc.list_token_costs(run_id=run.id, model_name="gpt-4o")
        assert total == 1
        assert items[0].model_name == "gpt-4o"

    def test_update_token_cost_recomputes_total_tokens(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        cost = svc.create_token_cost(
            TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o", input_tokens=100, output_tokens=50)
        )
        assert cost.total_tokens == 150

        updated = svc.update_token_cost(cost.id, TokenCostLedgerUpdate(input_tokens=200))
        assert updated.total_tokens == 250

    def test_delete_token_cost_deletes_cost_row(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)
        cost = svc.create_token_cost(TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o"))

        res = svc.delete_token_cost(cost.id)
        assert res is True
        with pytest.raises(NotFoundError):
            svc.get_token_cost(cost.id)


# ══════════════════════════════════════════════════════════════════════════════
# Trace Bundle and Cost Summary Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTraceBundleAndCostSummary:

    def test_get_trace_bundle_returns_counts(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        # Seed observability records
        svc.create_agent_trace(AgentTraceCreate(run_id=run.id, agent_name="agent", status="started"))
        svc.create_prompt_log(PromptLogCreate(run_id=run.id, agent_name="agent", prompt_text="Prompt text"))
        svc.create_memory_io_log(MemoryIOLogCreate(run_id=run.id, operation="read", memory_type="concept"))
        svc.create_token_cost(TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o", input_tokens=10, output_tokens=5))

        bundle = svc.get_trace_bundle(run.id)
        assert bundle.run_id == run.id
        assert bundle.total_trace_records == 1
        assert bundle.total_prompt_logs == 1
        assert bundle.total_memory_io_records == 1
        assert bundle.total_token_cost_records == 1
        assert bundle.status == "ready"

    def test_get_run_cost_summary_sums_token_fields(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        svc.create_token_cost(
            TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o", input_tokens=1000, output_tokens=500, estimated_cost=Decimal("0.01"))
        )
        svc.create_token_cost(
            TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o", input_tokens=2000, output_tokens=1000, estimated_cost=Decimal("0.02"))
        )

        summary = svc.get_run_cost_summary(run.id)
        assert summary.run_id == run.id
        assert summary.total_input_tokens == 3000
        assert summary.total_output_tokens == 1500
        assert summary.total_tokens == 4500
        assert float(summary.total_estimated_cost) == 0.03

    def test_get_run_cost_summary_includes_model_breakdown(self, db):
        book = _make_book(db)
        run = _make_run(db, book.id)
        svc = ObservabilityService(db)

        svc.create_token_cost(
            TokenCostLedgerCreate(run_id=run.id, model_name="gpt-4o", input_tokens=1000, output_tokens=500, estimated_cost=Decimal("0.01"))
        )
        svc.create_token_cost(
            TokenCostLedgerCreate(run_id=run.id, model_name="claude-3-5", input_tokens=2000, output_tokens=1000, estimated_cost=Decimal("0.05"))
        )

        summary = svc.get_run_cost_summary(run.id)
        assert "gpt-4o" in summary.model_breakdown
        assert "claude-3-5" in summary.model_breakdown
        assert summary.model_breakdown["gpt-4o"]["input_tokens"] == 1000
        assert summary.model_breakdown["claude-3-5"]["input_tokens"] == 2000


# ══════════════════════════════════════════════════════════════════════════════
# Error Behavior Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestObservabilityErrors:

    def test_get_missing_trace_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_agent_trace(uuid4())
        assert exc.value.code == "trace_not_found"

    def test_get_missing_prompt_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_prompt_log(uuid4())
        assert exc.value.code == "prompt_log_not_found"

    def test_get_missing_memory_io_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_memory_io_log(uuid4())
        assert exc.value.code == "memory_io_log_not_found"

    def test_get_missing_token_cost_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_token_cost(uuid4())
        assert exc.value.code == "token_cost_not_found"

    def test_get_trace_bundle_missing_run_raises_not_found(self, db):
        svc = ObservabilityService(db)
        with pytest.raises(NotFoundError) as exc:
            svc.get_trace_bundle(uuid4())
        assert exc.value.code == "run_not_found"
