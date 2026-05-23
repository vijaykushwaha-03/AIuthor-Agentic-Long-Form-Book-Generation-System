"""
AIuthor Backend — LLM Pydantic Schemas.

Defines the unified request/response envelope shared by all providers.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── LLMMessage ────────────────────────────────────────────────────────────────

class LLMMessage(BaseModel):
    """A single message in a conversation thread."""

    role: str = Field(..., description="Message role: system | user | assistant")
    content: str = Field(..., min_length=1, description="Message text content.")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid = {"system", "user", "assistant"}
        if v not in valid:
            raise ValueError(f"role must be one of {valid}, got '{v}'")
        return v


# ── LLMRequest ────────────────────────────────────────────────────────────────

class LLMRequest(BaseModel):
    """Unified generation request sent to any provider."""

    messages: list[LLMMessage] = Field(
        ...,
        min_length=1,
        description="Ordered list of conversation messages. Must have at least 1.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override. Falls back to provider default.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature override (0.0–2.0).",
    )
    max_output_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens in the response.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary key/value context passed through for observability.",
    )


# ── LLMResponse ───────────────────────────────────────────────────────────────

class LLMResponse(BaseModel):
    """Normalised response returned from any provider."""

    provider: str = Field(..., description="Provider name that generated this response.")
    model: str = Field(..., description="Model name used for this response.")
    content: str = Field(..., description="Generated text content.")
    input_tokens: int | None = Field(default=None, description="Prompt token count.")
    output_tokens: int | None = Field(default=None, description="Completion token count.")
    total_tokens: int | None = Field(default=None, description="Total token count.")
    raw_response: dict[str, Any] | None = Field(
        default=None,
        description="Raw SDK response payload (optional, for debugging).",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Pass-through metadata from the originating request.",
    )


# ── LLMProviderInfo ───────────────────────────────────────────────────────────

class LLMProviderInfo(BaseModel):
    """Provider capability summary returned by the status endpoint."""

    provider: str = Field(..., description="Provider identifier (gemini | openai | mock).")
    model: str = Field(..., description="Default model name for this provider.")
    configured: bool = Field(
        ...,
        description="True if the required API key is present (or provider is mock).",
    )
    supports_streaming: bool = Field(
        default=False,
        description="Whether the provider supports streaming (not yet implemented).",
    )
