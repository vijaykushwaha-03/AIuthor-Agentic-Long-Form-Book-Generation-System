from __future__ import annotations

import pytest
from pydantic import ValidationError
from uuid import uuid4
from datetime import datetime

from app.schemas import (
    BaseSchema,
    IDSchema,
    TimestampSchema,
    ORMBaseSchema,
    TonePreset,
    BookStatus,
    RunStatus,
    ChapterStatus,
    SectionStatus,
    AgentName,
    AgentStatus,
    MemoryOperation,
    EvalStatus,
    ExportType,
    ExportStatus,
    PaginationParams,
    PaginatedResponse,
    SortParams,
    MessageResponse,
    HealthResponse,
    VersionResponse,
    ErrorResponse,
    ValidationErrorResponse,
    InternalErrorResponse,
)


def test_package_exports():
    """Verify all schemas and enums are properly exported from the package."""
    assert BaseSchema is not None
    assert IDSchema is not None
    assert TimestampSchema is not None
    assert ORMBaseSchema is not None
    assert TonePreset is not None
    assert BookStatus is not None
    assert RunStatus is not None
    assert ChapterStatus is not None
    assert SectionStatus is not None
    assert AgentName is not None
    assert AgentStatus is not None
    assert MemoryOperation is not None
    assert EvalStatus is not None
    assert ExportType is not None
    assert ExportStatus is not None
    assert PaginationParams is not None
    assert PaginatedResponse is not None
    assert SortParams is not None
    assert MessageResponse is not None
    assert HealthResponse is not None
    assert VersionResponse is not None
    assert ErrorResponse is not None
    assert ValidationErrorResponse is not None
    assert InternalErrorResponse is not None


def test_base_schema_from_attributes():
    """Verify BaseSchema supports object attribute mapping (from_attributes=True)."""
    class DummyObj:
        def __init__(self, name: str, age: int):
            self.name = name
            self.age = age

    class DummySchema(BaseSchema):
        name: str
        age: int

    obj = DummyObj("Alice", 30)
    schema_obj = DummySchema.model_validate(obj)
    assert schema_obj.name == "Alice"
    assert schema_obj.age == 30


def test_orm_base_schema_lifecycle():
    """Verify ORMBaseSchema mapping and fields validation."""
    class DummyORM:
        def __init__(self, id_val, created_at, updated_at):
            self.id = id_val
            self.created_at = created_at
            self.updated_at = updated_at

    id_val = uuid4()
    now = datetime.now()
    orm_obj = DummyORM(id_val, now, now)

    schema_obj = ORMBaseSchema.model_validate(orm_obj)
    assert schema_obj.id == id_val
    assert schema_obj.created_at == now
    assert schema_obj.updated_at == now


def test_tone_presets():
    """Verify TonePreset enums match the required presets exactly."""
    expected = {"conversational", "academic", "storyteller", "motivational", "witty"}
    actual = {t.value for t in TonePreset}
    assert actual == expected


def test_pagination_params_valid():
    """Verify PaginationParams works with valid values or default values."""
    params = PaginationParams()
    assert params.page == 1
    assert params.page_size == 20

    params2 = PaginationParams(page=5, page_size=50)
    assert params2.page == 5
    assert params2.page_size == 50


def test_pagination_params_invalid():
    """Verify PaginationParams rejects invalid page or page_size values."""
    with pytest.raises(ValidationError):
        PaginationParams(page=0)

    with pytest.raises(ValidationError):
        PaginationParams(page_size=0)

    with pytest.raises(ValidationError):
        PaginationParams(page_size=101)


def test_sort_params_valid():
    """Verify SortParams accepts valid order parameters."""
    p1 = SortParams(sort_by="title", sort_order="asc")
    assert p1.sort_order == "asc"

    p2 = SortParams(sort_by="created_at", sort_order="desc")
    assert p2.sort_order == "desc"

    p3 = SortParams()
    assert p3.sort_order == "desc"


def test_sort_params_invalid():
    """Verify SortParams rejects invalid sort orders."""
    with pytest.raises(ValidationError):
        SortParams(sort_order="invalid_order")


def test_error_responses_instantiation():
    """Verify instantiation of basic error responses."""
    err = ErrorResponse(message="Resource not found", type="not_found_error")
    assert err.error is True
    assert err.message == "Resource not found"
    assert err.type == "not_found_error"
    assert err.details is None


def test_validation_error_response_defaults():
    """Verify ValidationErrorResponse default values are correct."""
    err = ValidationErrorResponse(details={"field": "required"})
    assert err.error is True
    assert err.message == "Validation error"
    assert err.type == "validation_error"
    assert err.details == {"field": "required"}


def test_internal_error_response_defaults():
    """Verify InternalErrorResponse default values are correct."""
    err = InternalErrorResponse()
    assert err.error is True
    assert err.message == "Internal server error"
    assert err.type == "internal_error"
