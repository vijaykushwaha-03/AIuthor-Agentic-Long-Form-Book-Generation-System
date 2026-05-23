"""
AIuthor Backend — Shared API Error Handler.

Centralises the service-exception → HTTP-exception mapping that was
duplicated across routes_books.py and routes_runs.py.  Importing from
here keeps individual route files thin.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.services.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationServiceError,
    ConflictError,
)


def handle_service_error(exc: Exception) -> None:
    """
    Map service-layer exceptions to FastAPI HTTP exceptions.

    Call this inside a route's ``except`` block to produce clean JSON
    error responses without exposing stack traces.

    Raises:
        HTTPException: Always — never returns normally.
    """
    if isinstance(exc, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    if isinstance(exc, ValidationServiceError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    if isinstance(exc, ConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    if isinstance(exc, ServiceError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "code": exc.code, "details": exc.details},
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"message": str(exc), "code": "internal_error"},
    )
