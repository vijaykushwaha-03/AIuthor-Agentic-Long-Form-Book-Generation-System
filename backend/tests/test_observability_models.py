from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.book import BookProject
from app.models.run import BookRun
from app.models.observability import (
    AgentTrace,
    PromptLog,
    MemoryIOLog,
    TokenCostLedger,
)


def test_base_metadata_contains_observability_tables():
    """Verify that all observability tables are registered in SQLAlchemy metadata."""
    expected_tables = {
        "agent_traces",
        "prompt_logs",
        "memory_io_logs",
        "token_cost_ledger",
    }
    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_observability_models_lifecycle():
    """Verify instantiation, relationships, defaults, cascades, and constraints on SQLite."""
    # Setup in-memory SQLite database for isolated unit test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. Instantiate BookProject
        project = BookProject(
            topic="Beginner Personal Finance Guide",
            reader_profile="Young adults aged 18-25 seeking basic budget tips",
            genre="Finance",
            tone="Conversational",
            target_chapters=10,
            words_per_chapter=2000,
            status="created",
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # 2. Instantiate BookRun
        run = BookRun(
            book_id=project.id,
            status="pending",
            current_agent="PlannerAgent",
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        # 3. Instantiate AgentTrace
        trace = AgentTrace(
            run_id=run.id,
            book_id=project.id,
            agent_name="planner",
            input_summary="Outline request",
            output_summary="Outline generated",
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            trace_metadata={"graph_step": 1},
        )
        session.add(trace)
        session.commit()
        session.refresh(trace)

        assert isinstance(trace.id, uuid.UUID)
        assert trace.run_id == run.id
        assert trace.book_id == project.id
        assert trace.agent_name == "planner"
        assert trace.input_summary == "Outline request"
        assert trace.output_summary == "Outline generated"
        assert trace.status == "completed"
        assert isinstance(trace.started_at, datetime)
        assert isinstance(trace.completed_at, datetime)
        assert trace.trace_metadata == {"graph_step": 1}
        assert trace.run == run
        assert trace.book == project
        assert trace in run.traces
        assert trace in project.agent_traces
        assert isinstance(trace.created_at, datetime)
        assert isinstance(trace.updated_at, datetime)

        # 4. Instantiate PromptLog
        prompt = PromptLog(
            run_id=run.id,
            book_id=project.id,
            agent_name="writer",
            model_name="gpt-4o",
            prompt_name="write_chapter",
            prompt_text="Write a chapter about saving money.",
            input_payload={"topic": "saving"},
            output_payload={"draft": "Save money daily..."},
        )
        session.add(prompt)
        session.commit()
        session.refresh(prompt)

        assert isinstance(prompt.id, uuid.UUID)
        assert prompt.run_id == run.id
        assert prompt.book_id == project.id
        assert prompt.agent_name == "writer"
        assert prompt.model_name == "gpt-4o"
        assert prompt.prompt_name == "write_chapter"
        assert prompt.prompt_text == "Write a chapter about saving money."
        assert prompt.input_payload == {"topic": "saving"}
        assert prompt.output_payload == {"draft": "Save money daily..."}
        assert prompt.run == run
        assert prompt.book == project
        assert prompt in run.prompt_logs
        assert prompt in project.prompt_logs

        # 5. Instantiate MemoryIOLog
        mem_log = MemoryIOLog(
            run_id=run.id,
            book_id=project.id,
            agent_name="memory_keeper",
            operation="write",
            memory_type="fact_registry",
            payload={"claim": "Compound interest is useful"},
        )
        session.add(mem_log)
        session.commit()
        session.refresh(mem_log)

        assert isinstance(mem_log.id, uuid.UUID)
        assert mem_log.run_id == run.id
        assert mem_log.book_id == project.id
        assert mem_log.agent_name == "memory_keeper"
        assert mem_log.operation == "write"
        assert mem_log.memory_type == "fact_registry"
        assert mem_log.payload == {"claim": "Compound interest is useful"}
        assert mem_log.run == run
        assert mem_log.book == project
        assert mem_log in run.memory_io_logs
        assert mem_log in project.memory_io_logs

        # 6. Instantiate TokenCostLedger (verifying default values)
        ledger = TokenCostLedger(
            run_id=run.id,
            book_id=project.id,
            agent_name="writer",
            model_name="gpt-4o",
            estimated_cost=Decimal("0.0450"),
            ledger_metadata={"pricing_tier": "standard"},
        )

        session.add(ledger)
        session.commit()
        session.refresh(ledger)

        assert isinstance(ledger.id, uuid.UUID)
        assert ledger.run_id == run.id
        assert ledger.book_id == project.id
        assert ledger.agent_name == "writer"
        assert ledger.model_name == "gpt-4o"
        assert ledger.input_tokens == 0
        assert ledger.output_tokens == 0
        assert ledger.total_tokens == 0
        assert ledger.estimated_cost == Decimal("0.0450") or ledger.estimated_cost == 0.0450
        assert ledger.currency == "USD"
        assert ledger.ledger_metadata == {"pricing_tier": "standard"}
        assert ledger.run == run
        assert ledger.book == project
        assert ledger in run.token_cost_entries
        assert ledger in project.token_cost_entries

        # 7. Check run-level cascade delete behavior
        session.delete(run)
        session.commit()

        # Run deleted: traces, prompt_logs, memory_io_logs, token_cost_entries should be deleted
        # (since they are linked to BookRun with cascade delete-orphan, or SET NULL where appropriate)
        assert session.query(AgentTrace).filter_by(run_id=run.id).count() == 0
        assert session.query(PromptLog).filter_by(run_id=run.id).count() == 0
        # For memory_io_logs and token_cost_ledger, run_id is nullable and ForeignKey has ondelete="SET NULL"
        # However, the SQLAlchemy relationship config has cascade="all, delete-orphan", meaning deletions will delete them.
        assert session.query(MemoryIOLog).filter_by(run_id=run.id).count() == 0
        assert session.query(TokenCostLedger).filter_by(run_id=run.id).count() == 0
