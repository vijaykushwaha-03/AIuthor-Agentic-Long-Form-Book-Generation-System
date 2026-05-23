"""
AIuthor Backend — Service Layer Exceptions.

Service exceptions are raised by service methods and converted to
appropriate HTTP responses by the route layer. They carry no HTTP
status codes — that mapping is the route layer's responsibility.
"""
from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """
    Base class for all service-level exceptions.

    Attributes:
        message: Human-readable error description.
        code:    Machine-readable error code (e.g. "book_not_found").
        details: Optional extra context (e.g. {"book_id": "..."}).
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, code={self.code!r})"
        )


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist in the database."""


class ValidationServiceError(ServiceError):
    """Raised when service-level validation fails (distinct from Pydantic)."""


class ConflictError(ServiceError):
    """Raised when an operation conflicts with the current resource state."""
