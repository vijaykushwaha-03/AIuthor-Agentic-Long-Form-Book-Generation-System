from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import TonePreset, BookStatus


class BookProjectCreate(BaseSchema):
    """
    Schema for validating the brief when creating a new book project.
    """
    topic: str = Field(..., min_length=3, max_length=300)
    reader_profile: str = Field(..., min_length=3, max_length=500)
    genre: str = Field(..., min_length=2, max_length=100)
    tone: TonePreset
    target_chapters: int = Field(..., ge=1, le=50)
    words_per_chapter: int | None = Field(None, ge=300, le=10000)
    project_metadata: dict | None = None

    @field_validator("topic", "reader_profile", "genre", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class BookProjectUpdate(BaseSchema):
    """
    Schema for validating partial updates of a book project.
    """
    topic: str | None = Field(None, min_length=3, max_length=300)
    reader_profile: str | None = Field(None, min_length=3, max_length=500)
    genre: str | None = Field(None, min_length=2, max_length=100)
    tone: TonePreset | None = None
    target_chapters: int | None = Field(None, ge=1, le=50)
    words_per_chapter: int | None = Field(None, ge=300, le=10000)
    status: BookStatus | None = None
    project_metadata: dict | None = None

    @field_validator("topic", "reader_profile", "genre", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class BookProjectResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a book project.
    """
    topic: str
    reader_profile: str
    genre: str
    tone: str
    target_chapters: int
    words_per_chapter: int | None
    status: str
    project_metadata: dict | None


class BookProjectListItem(BaseSchema):
    """
    Lightweight summary schema for book listings and dashboards.
    """
    id: UUID
    topic: str
    genre: str
    tone: str
    target_chapters: int
    status: str
    created_at: datetime | None
    updated_at: datetime | None
