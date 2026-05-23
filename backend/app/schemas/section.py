from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import SectionStatus

# Section type constants used for structures evaluation and assembling
REQUIRED_FRONT_MATTER_SECTIONS = [
    "half_title",
    "title_page",
    "copyright",
    "dedication",
    "epigraph",
    "toc",
    "foreword",
    "preface",
    "acknowledgments",
    "introduction",
]

REQUIRED_BACK_MATTER_SECTIONS = [
    "afterword",
    "appendix",
    "glossary",
    "references",
    "about_author",
    "back_cover_copy",
]


class BookSectionCreate(BaseSchema):
    """
    Schema for creating front matter and back matter sections.
    """
    book_id: UUID
    section_type: str = Field(..., min_length=2, max_length=100)
    title: str | None = Field(None, max_length=300)
    content: str | None = None
    sort_order: int = Field(..., ge=0)
    status: SectionStatus = SectionStatus.DRAFT
    section_metadata: dict | None = None

    @field_validator("section_type", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class BookSectionUpdate(BaseSchema):
    """
    Schema for updating front matter and back matter sections.
    """
    section_type: str | None = Field(None, min_length=2, max_length=100)
    title: str | None = Field(None, max_length=300)
    content: str | None = None
    sort_order: int | None = Field(None, ge=0)
    status: SectionStatus | None = None
    section_metadata: dict | None = None

    @field_validator("section_type", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class BookSectionResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a front or back matter section.
    """
    book_id: UUID
    section_type: str
    title: str | None
    content: str | None
    sort_order: int
    status: str
    section_metadata: dict | None


class BookSectionListItem(BaseSchema):
    """
    Lightweight summary schema for listing front or back matter sections.
    """
    id: UUID
    book_id: UUID
    section_type: str
    title: str | None
    sort_order: int
    status: str
    updated_at: datetime | None
