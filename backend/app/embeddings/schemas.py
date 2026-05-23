"""
AIuthor Backend — Embedding Pydantic Schemas.

Defines the unified request/response envelope shared by all embedding providers.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── EmbeddingRequest ──────────────────────────────────────────────────────────

class EmbeddingRequest(BaseModel):
    """Unified embedding request sent to any provider."""

    texts: list[str] = Field(
        ...,
        min_length=1,
        description="List of texts to embed. Must contain at least 1 non-empty string.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override. Falls back to provider default.",
    )
    dimensions: int | None = Field(
        default=None,
        gt=0,
        description="Optional output dimensions override. Falls back to provider default.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary context passed through for observability.",
    )

    @field_validator("texts")
    @classmethod
    def validate_texts_non_empty(cls, v: list[str]) -> list[str]:
        for i, text in enumerate(v):
            if not text or not text.strip():
                raise ValueError(
                    f"texts[{i}] is empty or whitespace-only. "
                    "All texts must be non-empty strings."
                )
        return v


# ── EmbeddingItem ─────────────────────────────────────────────────────────────

class EmbeddingItem(BaseModel):
    """A single text's embedding result."""

    text_index: int = Field(
        ...,
        ge=0,
        description="Index of the source text in the original request.texts list.",
    )
    embedding: list[float] = Field(
        ...,
        min_length=1,
        description="The dense vector embedding.",
    )
    token_count: int | None = Field(
        default=None,
        description="Approximate token count for this text (provider-dependent).",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional item-level metadata.",
    )


# ── EmbeddingResponse ─────────────────────────────────────────────────────────

class EmbeddingResponse(BaseModel):
    """Normalised embedding response returned from any provider."""

    provider: str = Field(..., description="Provider name that generated embeddings.")
    model: str = Field(..., description="Model name used for this response.")
    dimensions: int = Field(..., gt=0, description="Actual embedding vector dimensions.")
    items: list[EmbeddingItem] = Field(
        ...,
        min_length=1,
        description="One EmbeddingItem per input text.",
    )
    raw_response: dict[str, Any] | None = Field(
        default=None,
        description="Raw SDK response payload (optional, for debugging).",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Pass-through metadata from the originating request.",
    )


# ── EmbeddingProviderInfo ─────────────────────────────────────────────────────

class EmbeddingProviderInfo(BaseModel):
    """Provider capability summary returned by the status endpoint."""

    provider: str = Field(..., description="Provider identifier (gemini | openai | mock).")
    model: str = Field(..., description="Default model name for this provider instance.")
    dimensions: int = Field(..., description="Default output vector dimensions.")
    configured: bool = Field(
        ...,
        description="True if the required API key is present (or provider is mock).",
    )
    supports_batching: bool = Field(
        default=True,
        description="Whether the provider supports batching multiple texts per call.",
    )
