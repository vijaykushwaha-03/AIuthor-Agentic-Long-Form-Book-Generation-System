from __future__ import annotations

from typing import Any
from app.schemas.base import BaseSchema


class ErrorResponse(BaseSchema):
    """
    Standard error envelope structure.
    """
    error: bool = True
    message: str
    type: str
    details: list | dict | None = None


class ValidationErrorResponse(ErrorResponse):
    """
    Error response structured specifically for validation failures.
    """
    message: str = "Validation error"
    type: str = "validation_error"


class InternalErrorResponse(BaseSchema):
    """
    Error response structured for unhandled server issues.
    """
    error: bool = True
    message: str = "Internal server error"
    type: str = "internal_error"
