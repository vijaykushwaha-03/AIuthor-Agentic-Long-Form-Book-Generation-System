from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import ExportType, ExportStatus


# ── Export File Schemas ──────────────────────────────────────────────────────

class ExportFileCreate(BaseSchema):
    """
    Schema for saving generated output file records.
    """
    book_id: UUID
    run_id: UUID | None = None
    export_type: ExportType | str
    file_path: str = Field(..., min_length=1, max_length=2000)
    file_name: str = Field(..., min_length=1, max_length=500)
    mime_type: str | None = Field(None, max_length=100)
    status: ExportStatus | str = Field(ExportStatus.CREATED, max_length=50)
    export_metadata: dict | None = None

    @field_validator("file_path", mode="before")
    @classmethod
    def strip_file_path(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("file_name", mode="before")
    @classmethod
    def strip_file_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("export_type")
    @classmethod
    def validate_export_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("export_type must not exceed 50 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("status must not exceed 50 characters")
        return v


class ExportFileUpdate(BaseSchema):
    """
    Schema for updating generated file records.
    """
    export_type: ExportType | str | None = None
    file_path: str | None = Field(None, min_length=1, max_length=2000)
    file_name: str | None = Field(None, min_length=1, max_length=500)
    mime_type: str | None = Field(None, max_length=100)
    status: ExportStatus | str | None = None
    export_metadata: dict | None = None

    @field_validator("file_path", mode="before")
    @classmethod
    def strip_file_path(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("file_name", mode="before")
    @classmethod
    def strip_file_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("export_type")
    @classmethod
    def validate_export_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("export_type must not exceed 50 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("status must not exceed 50 characters")
        return v


class ExportFileResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a single export file.
    """
    book_id: UUID
    run_id: UUID | None
    export_type: str
    file_path: str
    file_name: str
    mime_type: str | None
    status: str
    export_metadata: dict | None


class ExportFileListItem(BaseSchema):
    """
    Lightweight summary schema returned for file lists.
    """
    id: UUID
    book_id: UUID
    run_id: UUID | None
    export_type: str
    file_name: str
    mime_type: str | None
    status: str
    created_at: datetime | None = None


# ── Export Envelopes ──────────────────────────────────────────────────────────

class ExportBundleResponse(BaseSchema):
    """
    Response schema returning collections of all generated files for a run.
    """
    book_id: UUID
    run_id: UUID | None = None
    files: list[ExportFileResponse] = Field(default_factory=list)
    total_files: int = Field(0, ge=0)
    ready_files: int = Field(0, ge=0)
    failed_files: int = Field(0, ge=0)
    status: str
    message: str | None = None


class ExportRequest(BaseSchema):
    """
    Input schema requesting output file generation.
    """
    book_id: UUID
    run_id: UUID | None = None
    export_types: list[ExportType | str] = Field(..., min_length=1)
    include_trace_bundle: bool = False
    include_prompt_dossier: bool = False
    include_eval_report: bool = False

    @field_validator("export_types")
    @classmethod
    def validate_export_types(cls, v: list[Any]) -> list[Any]:
        if not v or len(v) < 1:
            raise ValueError("export_types must contain at least 1 item")
        return v


class ExportResponse(BaseSchema):
    """
    Response schema summarizing requested exports results.
    """
    book_id: UUID
    run_id: UUID | None = None
    requested_exports: list[str] = Field(..., min_length=1)
    created_files: list[ExportFileResponse] = Field(default_factory=list)
    status: str
    message: str | None = None

    @field_validator("requested_exports")
    @classmethod
    def validate_requested_exports(cls, v: list[str]) -> list[str]:
        if not v or len(v) < 1:
            raise ValueError("requested_exports must contain at least 1 item")
        return v
