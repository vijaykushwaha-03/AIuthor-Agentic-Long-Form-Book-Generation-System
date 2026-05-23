from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import EvalStatus


# ── Eval Result Schemas ──────────────────────────────────────────────────────

class EvalResultCreate(BaseSchema):
    """
    Schema for saving automated evaluation results.
    """
    run_id: UUID | None = None
    book_id: UUID
    eval_name: str = Field(..., min_length=2, max_length=100)
    score: float | None = Field(None, ge=0.0, le=1.0)
    status: EvalStatus | str
    details: dict | None = None

    @field_validator("eval_name", mode="before")
    @classmethod
    def strip_eval_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("status must not exceed 50 characters")
        return v


class EvalResultUpdate(BaseSchema):
    """
    Schema for updating evaluation records.
    """
    eval_name: str | None = Field(None, min_length=2, max_length=100)
    score: float | None = Field(None, ge=0.0, le=1.0)
    status: EvalStatus | str | None = None
    details: dict | None = None

    @field_validator("eval_name", mode="before")
    @classmethod
    def strip_eval_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("status must not exceed 50 characters")
        return v


class EvalResultResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for an evaluation result.
    """
    run_id: UUID | None
    book_id: UUID
    eval_name: str
    score: float | None
    status: str
    details: dict | None


# ── Eval Report Envelopes ─────────────────────────────────────────────────────

class EvalMetricSummary(BaseSchema):
    """
    Detailed metric summary item in the eval report list.
    """
    eval_name: str = Field(..., min_length=2, max_length=100)
    score: float | None = Field(None, ge=0.0, le=1.0)
    status: str
    passed: bool | None = None
    failure_count: int = Field(0, ge=0)
    warning_count: int = Field(0, ge=0)
    details: dict | None = None


class EvalReportResponse(BaseSchema):
    """
    Response schema representing the overall generation evaluation report.
    """
    run_id: UUID | None = None
    book_id: UUID
    overall_status: str
    overall_score: float | None = Field(None, ge=0.0, le=1.0)
    metrics: list[EvalMetricSummary] = Field(default_factory=list)
    total_evals: int = Field(0, ge=0)
    passed_evals: int = Field(0, ge=0)
    failed_evals: int = Field(0, ge=0)
    warning_evals: int = Field(0, ge=0)
    details: dict | None = None
