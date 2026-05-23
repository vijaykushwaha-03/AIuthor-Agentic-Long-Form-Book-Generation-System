from __future__ import annotations

from typing import Generic, TypeVar, List, Literal, Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema

T = TypeVar("T")


class PaginationParams(BaseSchema):
    """
    Standard pagination query parameters.
    """
    page: int = Field(1, ge=1, description="Page number, starting at 1")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page (1-100)")


class PaginatedResponse(BaseSchema, Generic[T]):
    """
    Generic envelope for paginated resource collections.
    """
    items: List[T]
    total: int = Field(..., ge=0, description="Total number of items in the resource list")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    pages: int = Field(..., ge=0, description="Total number of pages available")


class SortParams(BaseSchema):
    """
    Standard sorting parameters.
    """
    sort_by: str | None = Field(None, description="Field name to sort by")
    sort_order: Literal["asc", "desc"] = Field("desc", description="Sorting direction: 'asc' or 'desc'")

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        if v not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class MessageResponse(BaseSchema):
    """
    Standard informational or success message response.
    """
    message: str
    success: bool = True


class HealthResponse(BaseSchema):
    """
    Liveness and health check response status.
    """
    status: str
    env: str | None = None
    version: str | None = None


class VersionResponse(BaseSchema):
    """
    System and service version metadata.
    """
    version: str
    service: str
