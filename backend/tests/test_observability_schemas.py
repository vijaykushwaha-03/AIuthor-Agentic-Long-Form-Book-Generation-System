from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from app.schemas import (
    AgentTraceCreate,
    AgentTraceUpdate,
    AgentTraceResponse,
    PromptLogCreate,
    PromptLogUpdate,
    PromptLogResponse,
    MemoryIOLogCreate,
    MemoryIOLogResponse,
    TokenCostLedgerCreate,
    TokenCostLedgerUpdate,
    TokenCostLedgerResponse,
    TraceBundleResponse,
    RunCostSummaryResponse,
    AgentName,
    AgentStatus,
    MemoryOperation,
)


# ── 23. Package Exports Verification ──────────────────────────────────────────

def test_package_exports_observability():
    """Verify all observability schemas and types are properly imported from the schemas package."""
    assert AgentTraceCreate is not None
    assert AgentTraceUpdate is not None
    assert AgentTraceResponse is not None
    assert PromptLogCreate is not None
    assert PromptLogUpdate is not None
    assert PromptLogResponse is not None
    assert MemoryIOLogCreate is not None
    assert MemoryIOLogResponse is not None
    assert TokenCostLedgerCreate is not None
    assert TokenCostLedgerUpdate is not None
    assert TokenCostLedgerResponse is not None
    assert TraceBundleResponse is not None
    assert RunCostSummaryResponse is not None


# ── AgentTrace Tests ──────────────────────────────────────────────────────────

def test_agent_trace_create_valid():
    """1. Valid data passes validation for AgentTraceCreate."""
    run_id = uuid4()
    book_id = uuid4()
    schema = AgentTraceCreate(
        run_id=run_id,
        book_id=book_id,
        agent_name=AgentName.WRITER,
        input_summary="Writing chapter 1 draft.",
        output_summary="Draft complete.",
        status=AgentStatus.COMPLETED,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        trace_metadata={"retry_count": 0}
    )
    assert schema.run_id == run_id
    assert schema.book_id == book_id
    assert schema.agent_name == AgentName.WRITER
    assert schema.status == AgentStatus.COMPLETED


def test_agent_trace_create_input_summary_over_max():
    """2. input_summary over max length (5000) fails validation."""
    with pytest.raises(ValidationError):
        AgentTraceCreate(
            run_id=uuid4(),
            agent_name="writer",
            status="started",
            input_summary="a" * 5001
        )


def test_agent_trace_create_error_message_over_max():
    """3. error_message over max length (10000) fails validation."""
    with pytest.raises(ValidationError):
        AgentTraceCreate(
            run_id=uuid4(),
            agent_name="writer",
            status="failed",
            error_message="e" * 10001
        )


def test_agent_trace_update_valid_partial():
    """4. Partial status update passes validation for AgentTraceUpdate."""
    schema = AgentTraceUpdate(
        status=AgentStatus.COMPLETED,
        output_summary="Finished step successfully."
    )
    assert schema.status == AgentStatus.COMPLETED
    assert schema.output_summary == "Finished step successfully."
    assert schema.input_summary is None


# ── PromptLog Tests ───────────────────────────────────────────────────────────

def test_prompt_log_create_valid():
    """5. Valid data passes validation for PromptLogCreate."""
    run_id = uuid4()
    schema = PromptLogCreate(
        run_id=run_id,
        agent_name=AgentName.HUMANIZER,
        model_name="claude-3-opus",
        prompt_name="humanize-draft",
        prompt_text="Please humanize this text...",
        input_payload={"temperature": 0.7}
    )
    assert schema.run_id == run_id
    assert schema.prompt_text == "Please humanize this text..."
    assert schema.agent_name == AgentName.HUMANIZER


def test_prompt_log_create_prompt_text_too_short():
    """6. prompt_text too short fails validation (min_length=3 and stripped)."""
    with pytest.raises(ValidationError):
        PromptLogCreate(
            run_id=uuid4(),
            agent_name="humanizer",
            prompt_text="ab"
        )

    # Stripped whitespace-only text should reduce to empty string and fail
    with pytest.raises(ValidationError):
        PromptLogCreate(
            run_id=uuid4(),
            agent_name="humanizer",
            prompt_text="   "
        )


def test_prompt_log_create_model_name_too_long():
    """7. model_name over max length (100) fails validation."""
    with pytest.raises(ValidationError):
        PromptLogCreate(
            run_id=uuid4(),
            agent_name="writer",
            prompt_text="Valid prompt text",
            model_name="m" * 101
        )


# ── MemoryIOLog Tests ─────────────────────────────────────────────────────────

def test_memory_io_log_create_valid_read():
    """8. Valid read operation passes validation for MemoryIOLogCreate."""
    run_id = uuid4()
    schema = MemoryIOLogCreate(
        run_id=run_id,
        agent_name="writer",
        operation=MemoryOperation.READ,
        memory_type="CharacterBible",
        payload={"query": "Alice"}
    )
    assert schema.run_id == run_id
    assert schema.operation == MemoryOperation.READ
    assert schema.memory_type == "CharacterBible"


def test_memory_io_log_create_memory_type_too_short():
    """9. memory_type too short fails validation (min_length=2 and stripped)."""
    with pytest.raises(ValidationError):
        MemoryIOLogCreate(
            run_id=uuid4(),
            operation="read",
            memory_type="a"
        )

    with pytest.raises(ValidationError):
        MemoryIOLogCreate(
            run_id=uuid4(),
            operation="read",
            memory_type="   "
        )


# ── TokenCostLedger Tests ─────────────────────────────────────────────────────

def test_token_cost_ledger_create_valid():
    """10. Valid data passes validation for TokenCostLedgerCreate."""
    run_id = uuid4()
    schema = TokenCostLedgerCreate(
        run_id=run_id,
        agent_name="writer",
        model_name="gpt-4o",
        input_tokens=1500,
        output_tokens=500,
        total_tokens=2000,
        estimated_cost=Decimal("0.03"),
        currency="USD"
    )
    assert schema.run_id == run_id
    assert schema.input_tokens == 1500
    assert schema.estimated_cost == Decimal("0.03")
    assert schema.currency == "USD"


def test_token_cost_ledger_create_input_tokens_negative():
    """11. input_tokens below 0 fails validation."""
    with pytest.raises(ValidationError):
        TokenCostLedgerCreate(
            model_name="gpt-4o",
            input_tokens=-1
        )


def test_token_cost_ledger_create_output_tokens_negative():
    """12. output_tokens below 0 fails validation."""
    with pytest.raises(ValidationError):
        TokenCostLedgerCreate(
            model_name="gpt-4o",
            output_tokens=-10
        )


def test_token_cost_ledger_create_estimated_cost_negative():
    """13. estimated_cost below 0 fails validation."""
    with pytest.raises(ValidationError):
        TokenCostLedgerCreate(
            model_name="gpt-4o",
            estimated_cost=-0.001
        )


def test_token_cost_ledger_create_currency_too_long():
    """14. currency over max length (10) fails validation."""
    with pytest.raises(ValidationError):
        TokenCostLedgerCreate(
            model_name="gpt-4o",
            currency="USDollarExtra"
        )


def test_token_cost_ledger_response_orm():
    """15. TokenCostLedgerResponse validates from ORM-like object."""
    class MockLedgerModel:
        def __init__(self):
            self.id = uuid4()
            self.run_id = uuid4()
            self.book_id = uuid4()
            self.agent_name = "writer"
            self.model_name = "claude-3-haiku"
            self.input_tokens = 200
            self.output_tokens = 80
            self.total_tokens = 280
            self.estimated_cost = Decimal("0.0005")
            self.currency = "USD"
            self.ledger_metadata = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockLedgerModel()
    schema = TokenCostLedgerResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.model_name == "claude-3-haiku"
    assert schema.total_tokens == 280
    assert schema.estimated_cost == Decimal("0.0005")


# ── TraceBundleResponse Tests ─────────────────────────────────────────────────

def test_trace_bundle_response_valid_empty():
    """16. Valid empty bundle passes validation."""
    run_id = uuid4()
    schema = TraceBundleResponse(
        run_id=run_id,
        status="success",
        total_prompt_logs=0,
        total_trace_records=0
    )
    assert schema.run_id == run_id
    assert schema.status == "success"
    assert schema.traces == []
    assert schema.prompt_logs == []


def test_trace_bundle_response_negative_counters():
    """17. negative total_trace_records fails validation."""
    with pytest.raises(ValidationError):
        TraceBundleResponse(
            run_id=uuid4(),
            status="success",
            total_trace_records=-1
        )


# ── RunCostSummaryResponse Tests ──────────────────────────────────────────────

def test_run_cost_summary_response_valid():
    """18. Valid summary passes validation."""
    run_id = uuid4()
    schema = RunCostSummaryResponse(
        run_id=run_id,
        total_input_tokens=1000,
        total_output_tokens=500,
        total_tokens=1500,
        total_estimated_cost=Decimal("0.0225"),
        currency="USD",
        model_breakdown={"gpt-4o": 0.0225}
    )
    assert schema.run_id == run_id
    assert schema.total_tokens == 1500
    assert schema.total_estimated_cost == Decimal("0.0225")


def test_run_cost_summary_response_negative_tokens():
    """19. negative total_tokens fails validation."""
    with pytest.raises(ValidationError):
        RunCostSummaryResponse(
            run_id=uuid4(),
            total_tokens=-5
        )


# ── ORM Model Conversions Verification ─────────────────────────────────────────

def test_agent_trace_response_orm():
    """20. AgentTraceResponse validates from ORM-like object."""
    class MockTraceModel:
        def __init__(self):
            self.id = uuid4()
            self.run_id = uuid4()
            self.book_id = uuid4()
            self.agent_name = "writer"
            self.input_summary = "Start writing."
            self.output_summary = "End writing."
            self.status = "completed"
            self.error_message = None
            self.started_at = datetime.utcnow()
            self.completed_at = datetime.utcnow()
            self.trace_metadata = {"step": 1}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockTraceModel()
    schema = AgentTraceResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.agent_name == "writer"
    assert schema.status == "completed"


def test_prompt_log_response_orm():
    """21. PromptLogResponse validates from ORM-like object."""
    class MockPromptModel:
        def __init__(self):
            self.id = uuid4()
            self.run_id = uuid4()
            self.book_id = uuid4()
            self.agent_name = "writer"
            self.model_name = "gpt-4"
            self.prompt_name = "write-outline"
            self.prompt_text = "Prompt text instructions..."
            self.input_payload = {"temp": 0.2}
            self.output_payload = {"choices": []}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockPromptModel()
    schema = PromptLogResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.prompt_text == "Prompt text instructions..."
    assert schema.model_name == "gpt-4"


def test_memory_io_log_response_orm():
    """22. MemoryIOLogResponse validates from ORM-like object."""
    class MockMemoryIOModel:
        def __init__(self):
            self.id = uuid4()
            self.run_id = uuid4()
            self.book_id = uuid4()
            self.agent_name = "writer"
            self.operation = "write"
            self.memory_type = "ConceptBible"
            self.payload = {"concept": "Gravity"}
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()

    mock_obj = MockMemoryIOModel()
    schema = MemoryIOLogResponse.model_validate(mock_obj)
    assert schema.id == mock_obj.id
    assert schema.operation == "write"
    assert schema.memory_type == "ConceptBible"
