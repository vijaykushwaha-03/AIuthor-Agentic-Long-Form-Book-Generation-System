from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema, ORMBaseSchema
from app.schemas.enums import TonePreset, MemoryOperation


# ── Fact Registry Schemas ────────────────────────────────────────────────────

class FactRegistryCreate(BaseSchema):
    """
    Schema for saving fact claims and grounding evidence.
    """
    book_id: UUID
    chapter_id: UUID | None = None
    claim: str = Field(..., min_length=3, max_length=5000)
    source_document_id: UUID | None = None
    source_chunk_id: UUID | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    status: str = Field("unverified", max_length=50)
    used_in_chapters: list[int] | None = None
    fact_metadata: dict | None = None

    @field_validator("claim", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("used_in_chapters")
    @classmethod
    def validate_used_chapters(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for ch in v:
                if ch < 1:
                    raise ValueError("used_in_chapters values must be >= 1")
        return v


class FactRegistryUpdate(BaseSchema):
    """
    Schema for updating fact claims and evidence status.
    """
    chapter_id: UUID | None = None
    claim: str | None = Field(None, min_length=3, max_length=5000)
    source_document_id: UUID | None = None
    source_chunk_id: UUID | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    status: str | None = Field(None, max_length=50)
    used_in_chapters: list[int] | None = None
    fact_metadata: dict | None = None

    @field_validator("claim", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("used_in_chapters")
    @classmethod
    def validate_used_chapters(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for ch in v:
                if ch < 1:
                    raise ValueError("used_in_chapters values must be >= 1")
        return v


class FactRegistryResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a fact record.
    """
    book_id: UUID
    chapter_id: UUID | None
    claim: str
    source_document_id: UUID | None
    source_chunk_id: UUID | None
    confidence: float | None
    status: str
    used_in_chapters: list[int] | dict | None
    fact_metadata: dict | None


# ── Concept Bible Schemas ────────────────────────────────────────────────────

class ConceptBibleCreate(BaseSchema):
    """
    Schema for saving recurring concepts and glossary definitions.
    """
    book_id: UUID
    concept: str = Field(..., min_length=2, max_length=300)
    definition: str | None = Field(None, max_length=5000)
    first_chapter: int | None = Field(None, ge=1)
    related_terms: list[str] | None = None
    appears_in_chapters: list[int] | None = None
    concept_metadata: dict | None = None

    @field_validator("concept", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("appears_in_chapters")
    @classmethod
    def validate_appears_chapters(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for ch in v:
                if ch < 1:
                    raise ValueError("appears_in_chapters values must be >= 1")
        return v

    @field_validator("related_terms")
    @classmethod
    def validate_related_terms(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for term in v:
                if not term or not term.strip():
                    raise ValueError("related_terms entries should be non-empty strings")
        return v


class ConceptBibleUpdate(BaseSchema):
    """
    Schema for updating concept definition and associated chapters.
    """
    concept: str | None = Field(None, min_length=2, max_length=300)
    definition: str | None = Field(None, max_length=5000)
    first_chapter: int | None = Field(None, ge=1)
    related_terms: list[str] | None = None
    appears_in_chapters: list[int] | None = None
    concept_metadata: dict | None = None

    @field_validator("concept", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("appears_in_chapters")
    @classmethod
    def validate_appears_chapters(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for ch in v:
                if ch < 1:
                    raise ValueError("appears_in_chapters values must be >= 1")
        return v

    @field_validator("related_terms")
    @classmethod
    def validate_related_terms(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            for term in v:
                if not term or not term.strip():
                    raise ValueError("related_terms entries should be non-empty strings")
        return v


class ConceptBibleResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a concept.
    """
    book_id: UUID
    concept: str
    definition: str | None
    first_chapter: int | None
    related_terms: list[str] | dict | None
    appears_in_chapters: list[int] | dict | None
    concept_metadata: dict | None


# ── Character Bible Schemas ──────────────────────────────────────────────────

class CharacterBibleCreate(BaseSchema):
    """
    Schema for saving characters and character continuity details.
    """
    book_id: UUID
    character_name: str = Field(..., min_length=2, max_length=200)
    role: str | None = Field(None, max_length=500)
    traits: list[str] | dict | None = None
    relationships: dict | None = None
    arc_summary: str | None = Field(None, max_length=5000)
    appears_in_chapters: list[int] | None = None
    character_metadata: dict | None = None

    @field_validator("character_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("appears_in_chapters")
    @classmethod
    def validate_appears_chapters(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for ch in v:
                if ch < 1:
                    raise ValueError("appears_in_chapters values must be >= 1")
        return v


class CharacterBibleUpdate(BaseSchema):
    """
    Schema for updating character details, traits, and arc summaries.
    """
    character_name: str | None = Field(None, min_length=2, max_length=200)
    role: str | None = Field(None, max_length=500)
    traits: list[str] | dict | None = None
    relationships: dict | None = None
    arc_summary: str | None = Field(None, max_length=5000)
    appears_in_chapters: list[int] | None = None
    character_metadata: dict | None = None

    @field_validator("character_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("appears_in_chapters")
    @classmethod
    def validate_appears_chapters(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            for ch in v:
                if ch < 1:
                    raise ValueError("appears_in_chapters values must be >= 1")
        return v


class CharacterBibleResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a character.
    """
    book_id: UUID
    character_name: str
    role: str | None
    traits: list[str] | dict | None
    relationships: dict | None
    arc_summary: str | None
    appears_in_chapters: list[int] | dict | None
    character_metadata: dict | None


# ── Callback Index Schemas ───────────────────────────────────────────────────

class CallbackIndexCreate(BaseSchema):
    """
    Schema for saving cross-chapter continuity callback references.
    """
    book_id: UUID
    source_chapter: int | None = Field(None, ge=1)
    target_chapter: int | None = Field(None, ge=1)
    concept: str | None = Field(None, max_length=300)
    callback_text: str = Field(..., min_length=3, max_length=5000)
    status: str = Field("active", max_length=50)
    callback_metadata: dict | None = None

    @field_validator("callback_text", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class CallbackIndexUpdate(BaseSchema):
    """
    Schema for updating callback references during repair flows.
    """
    source_chapter: int | None = Field(None, ge=1)
    target_chapter: int | None = Field(None, ge=1)
    concept: str | None = Field(None, max_length=300)
    callback_text: str | None = Field(None, min_length=3, max_length=5000)
    status: str | None = Field(None, max_length=50)
    callback_metadata: dict | None = None

    @field_validator("callback_text", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class CallbackIndexResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a callback entry.
    """
    book_id: UUID
    source_chapter: int | None
    target_chapter: int | None
    concept: str | None
    callback_text: str
    status: str
    callback_metadata: dict | None


# ── Tone Fingerprint Schemas ─────────────────────────────────────────────────

class ToneFingerprintCreate(BaseSchema):
    """
    Schema for saving tone fingerprint sentence rhythms and lexical rules.
    """
    book_id: UUID
    tone_name: TonePreset | str
    sentence_rhythm: dict | None = None
    lexical_rules: dict | None = None
    banned_phrases: list[str] | dict | None = None
    example_phrases: list[str] | dict | None = None
    fingerprint_metadata: dict | None = None

    @field_validator("tone_name")
    @classmethod
    def validate_tone_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("tone_name must not exceed 50 characters")
        return v

    @field_validator("banned_phrases")
    @classmethod
    def validate_banned_phrases(cls, v: list[str] | dict | None) -> list[str] | dict | None:
        if isinstance(v, list):
            for phrase in v:
                if not phrase or not phrase.strip():
                    raise ValueError("banned_phrases entries should be non-empty strings")
        return v

    @field_validator("example_phrases")
    @classmethod
    def validate_example_phrases(cls, v: list[str] | dict | None) -> list[str] | dict | None:
        if isinstance(v, list):
            for phrase in v:
                if not phrase or not phrase.strip():
                    raise ValueError("example_phrases entries should be non-empty strings")
        return v


class ToneFingerprintUpdate(BaseSchema):
    """
    Schema for updating tone rules and phrase lists.
    """
    tone_name: TonePreset | str | None = None
    sentence_rhythm: dict | None = None
    lexical_rules: dict | None = None
    banned_phrases: list[str] | dict | None = None
    example_phrases: list[str] | dict | None = None
    fingerprint_metadata: dict | None = None

    @field_validator("tone_name")
    @classmethod
    def validate_tone_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            if len(v) > 50:
                raise ValueError("tone_name must not exceed 50 characters")
        return v

    @field_validator("banned_phrases")
    @classmethod
    def validate_banned_phrases(cls, v: list[str] | dict | None) -> list[str] | dict | None:
        if isinstance(v, list):
            for phrase in v:
                if not phrase or not phrase.strip():
                    raise ValueError("banned_phrases entries should be non-empty strings")
        return v

    @field_validator("example_phrases")
    @classmethod
    def validate_example_phrases(cls, v: list[str] | dict | None) -> list[str] | dict | None:
        if isinstance(v, list):
            for phrase in v:
                if not phrase or not phrase.strip():
                    raise ValueError("example_phrases entries should be non-empty strings")
        return v


class ToneFingerprintResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a tone fingerprint.
    """
    book_id: UUID
    tone_name: str
    sentence_rhythm: dict | None
    lexical_rules: dict | None
    banned_phrases: list[str] | dict | None
    example_phrases: list[str] | dict | None
    fingerprint_metadata: dict | None


# ── Decision Log Schemas ─────────────────────────────────────────────────────

class DecisionLogCreate(BaseSchema):
    """
    Schema for logging critical generation and formatting decisions.
    """
    book_id: UUID | None = None
    decision: str = Field(..., min_length=3, max_length=5000)
    reason: str | None = Field(None, max_length=5000)
    impact: str | None = Field(None, max_length=5000)
    decision_metadata: dict | None = None

    @field_validator("decision", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class DecisionLogUpdate(BaseSchema):
    """
    Schema for updating logged decisions and outcomes.
    """
    decision: str | None = Field(None, min_length=3, max_length=5000)
    reason: str | None = Field(None, max_length=5000)
    impact: str | None = Field(None, max_length=5000)
    decision_metadata: dict | None = None

    @field_validator("decision", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class DecisionLogResponse(ORMBaseSchema):
    """
    Detailed response schema returned by APIs for a decision log.
    """
    book_id: UUID | None
    decision: str
    reason: str | None
    impact: str | None
    decision_metadata: dict | None


# ── Memory Envelope Schemas ──────────────────────────────────────────────────

class MemoryReadRequest(BaseSchema):
    """
    Request schema to query the memory system.
    """
    book_id: UUID
    memory_types: list[str] | None = None
    chapter_number: int | None = Field(None, ge=1)
    query: str | None = Field(None, max_length=1000)
    limit: int = Field(20, ge=1, le=100)


class MemoryReadResponse(BaseSchema):
    """
    Response schema returning collections of relevant retrieved memories.
    """
    book_id: UUID
    facts: list[FactRegistryResponse] = Field(default_factory=list)
    concepts: list[ConceptBibleResponse] = Field(default_factory=list)
    characters: list[CharacterBibleResponse] = Field(default_factory=list)
    callbacks: list[CallbackIndexResponse] = Field(default_factory=list)
    tone_fingerprints: list[ToneFingerprintResponse] = Field(default_factory=list)
    decisions: list[DecisionLogResponse] = Field(default_factory=list)
    total_items: int = Field(..., ge=0)


class MemoryWriteRequest(BaseSchema):
    """
    Input schema to save or append memories generated during execution.
    """
    book_id: UUID
    operation: MemoryOperation = MemoryOperation.WRITE
    facts: list[FactRegistryCreate] = Field(default_factory=list)
    concepts: list[ConceptBibleCreate] = Field(default_factory=list)
    characters: list[CharacterBibleCreate] = Field(default_factory=list)
    callbacks: list[CallbackIndexCreate] = Field(default_factory=list)
    tone_fingerprints: list[ToneFingerprintCreate] = Field(default_factory=list)
    decisions: list[DecisionLogCreate] = Field(default_factory=list)


class MemoryWriteResponse(BaseSchema):
    """
    Response schema summarizing memory write outcomes.
    """
    book_id: UUID
    operation: str
    created_counts: dict
    updated_counts: dict | None = None
    status: str
    message: str | None = None
