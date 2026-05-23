"""
AIuthor Backend — LLM Exception Hierarchy.

All LLM-specific exceptions inherit from LLMError so callers can
catch the whole family with a single except clause.
"""
from __future__ import annotations

from typing import Any


class LLMError(Exception):
    """
    Base class for all LLM-layer exceptions.

    Attributes:
        message:  Human-readable description.
        provider: Which provider raised the error (optional).
        details:  Extra structured context (optional).
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, provider={self.provider!r})"
        )


class LLMConfigurationError(LLMError):
    """
    Raised when a provider cannot be initialised due to missing or invalid
    configuration (e.g. missing API key, unknown provider name).
    """


class LLMProviderError(LLMError):
    """
    Raised when a provider call fails at runtime (network error, rate limit,
    unexpected SDK error, malformed response, etc.).
    """
