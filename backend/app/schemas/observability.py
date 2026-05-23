from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import AgentName, AgentStatus, MemoryOperation


# ── Agent Trace Schemas ──────────────────────────────────────────────────────

class AgentTraceCreate(BaseSchema):
    """
    Schema for creating trace records for agent execution.
    """
    run_id: UUID
    book_id: UUID | None = None
    agent_name: AgentName | str
    input_summary: str | None = Field(None, max_length=5000)
    output_summary: str | None = Field(None, max_length=5000)
    status: AgentStatus | str
    error_message: str | None = Field(None, max_length=10000)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    trace_metadata: dict | None = None

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 100:
                raise ValueError("agent_name must not exceed 100 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("status must not exceed 50 characters")
        return v


class AgentTraceUpdate(BaseSchema):
    """
    Schema for updating trace status from started to completed/failed.
    """
    input_summary: str | None = Field(None, max_length=5000)
    output_summary: str | None = Field(None, max_length=5000)
    status: AgentStatus | str | None = None
    error_message: str | None = Field(None, max_length=10000)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    trace_metadata: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("status must not exceed 50 characters")
        return v


class AgentTraceResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for agent trace records.
    """
    run_id: UUID
    book_id: UUID | None
    agent_name: str
    input_summary: str | None
    output_summary: str | None
    status: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    trace_metadata: dict | None


# ── Prompt Log Schemas ────────────────────────────────────────────────────────

class PromptLogCreate(BaseSchema):
    """
    Schema for storing complete prompts for dossier extraction and debugging.
    """
    run_id: UUID
    book_id: UUID | None = None
    agent_name: AgentName | str
    model_name: str | None = Field(None, max_length=100)
    prompt_name: str | None = Field(None, max_length=100)
    prompt_text: str = Field(..., min_length=3)
    input_payload: dict | None = None
    output_payload: dict | None = None

    @field_validator("prompt_text", mode="before")
    @classmethod
    def strip_prompt_text(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 100:
                raise ValueError("agent_name must not exceed 100 characters")
        return v


class PromptLogUpdate(BaseSchema):
    """
    Schema for updating prompt details.
    """
    model_name: str | None = Field(None, max_length=100)
    prompt_name: str | None = Field(None, max_length=100)
    prompt_text: str | None = Field(None, min_length=3)
    input_payload: dict | None = None
    output_payload: dict | None = None

    @field_validator("prompt_text", mode="before")
    @classmethod
    def strip_prompt_text(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class PromptLogResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for prompt log records.
    """
    run_id: UUID
    book_id: UUID | None
    agent_name: str
    model_name: str | None
    prompt_name: str | None
    prompt_text: str
    input_payload: dict | None
    output_payload: dict | None


# ── Memory I/O Log Schemas ───────────────────────────────────────────────────

class MemoryIOLogCreate(BaseSchema):
    """
    Schema for logging every memory read/write operation.
    """
    run_id: UUID | None = None
    book_id: UUID | None = None
    agent_name: AgentName | str | None = None
    operation: MemoryOperation | str
    memory_type: str = Field(..., min_length=2, max_length=100)
    payload: dict | None = None

    @field_validator("memory_type", mode="before")
    @classmethod
    def strip_memory_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 100:
                raise ValueError("agent_name must not exceed 100 characters")
        return v

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("operation must not exceed 50 characters")
        return v


class MemoryIOLogResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for memory operation logs.
    """
    run_id: UUID | None
    book_id: UUID | None
    agent_name: str | None
    operation: str
    memory_type: str
    payload: dict | None


# ── Token Cost Ledger Schemas ────────────────────────────────────────────────

class TokenCostLedgerCreate(BaseSchema):
    """
    Schema for tracking token usage and cost per model call.
    """
    run_id: UUID | None = None
    book_id: UUID | None = None
    agent_name: AgentName | str | None = None
    model_name: str = Field(..., min_length=2, max_length=100)
    input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    total_tokens: int | None = Field(None, ge=0)
    estimated_cost: Decimal | float | None = Field(None, ge=0.0)
    currency: str = Field("USD", max_length=10)
    ledger_metadata: dict | None = None

    @field_validator("model_name", mode="before")
    @classmethod
    def strip_model_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 100:
                raise ValueError("agent_name must not exceed 100 characters")
        return v


class TokenCostLedgerUpdate(BaseSchema):
    """
    Schema for updating token usage details.
    """
    input_tokens: int | None = Field(None, ge=0)
    output_tokens: int | None = Field(None, ge=0)
    total_tokens: int | None = Field(None, ge=0)
    estimated_cost: Decimal | float | None = Field(None, ge=0.0)
    currency: str | None = Field(None, max_length=10)
    ledger_metadata: dict | None = None


class TokenCostLedgerResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for token cost ledger records.
    """
    run_id: UUID | None
    book_id: UUID | None
    agent_name: str | None
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: Decimal | float | None
    currency: str
    ledger_metadata: dict | None


# ── Trace Bundle & Cost Summary Schemas ─────────────────────────────────────────

class TraceBundleResponse(BaseSchema):
    """
    Response schema returning complete traces for runs/exports.
    """
    run_id: UUID
    book_id: UUID | None = None
    traces: list[AgentTraceResponse] = Field(default_factory=list)
    prompt_logs: list[PromptLogResponse] = Field(default_factory=list)
    memory_io_logs: list[MemoryIOLogResponse] = Field(default_factory=list)
    token_cost_ledger: list[TokenCostLedgerResponse] = Field(default_factory=list)
    total_prompt_logs: int = Field(0, ge=0)
    total_trace_records: int = Field(0, ge=0)
    total_memory_io_records: int = Field(0, ge=0)
    total_token_cost_records: int = Field(0, ge=0)
    status: str
    message: str | None = None


class RunCostSummaryResponse(BaseSchema):
    """
    Response schema summarizing execution cost details.
    """
    run_id: UUID
    book_id: UUID | None = None
    total_input_tokens: int = Field(0, ge=0)
    total_output_tokens: int = Field(0, ge=0)
    total_tokens: int = Field(0, ge=0)
    total_estimated_cost: Decimal | float | None = Field(None, ge=0.0)
    currency: str = Field("USD", max_length=10)
    model_breakdown: dict | None = None
