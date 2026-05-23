"""
AIuthor Backend — Embedding Provider Factory.

Resolves the configured embedding provider and returns an instantiated
BaseEmbeddingProvider ready for use. Providers are created on demand —
never at app startup — so missing API keys don't block the server.
"""
from __future__ import annotations

import logging

from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.exceptions import EmbeddingConfigurationError
from app.embeddings.providers import (
    GeminiEmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
)

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = {"gemini", "openai", "mock"}


def get_embedding_provider(provider: str | None = None) -> BaseEmbeddingProvider:
    """
    Instantiate and return the requested embedding provider.

    Resolution order:
      1. ``provider`` argument (if given)
      2. ``settings.EMBEDDING_PROVIDER`` environment variable
      3. Falls back to ``"gemini"`` (built-in default)

    Args:
        provider: Explicit provider name override. One of
                  ``"gemini"``, ``"openai"``, or ``"mock"``.

    Returns:
        A fully configured BaseEmbeddingProvider instance.

    Raises:
        EmbeddingConfigurationError: If the provider name is unknown, or if a
            real provider's API key is missing.
    """
    from app.config import get_settings
    settings = get_settings()

    resolved = (provider or settings.EMBEDDING_PROVIDER or "gemini").lower()

    if resolved not in _SUPPORTED_PROVIDERS:
        raise EmbeddingConfigurationError(
            message=(
                f"Unknown embedding provider '{resolved}'. "
                f"Supported providers: {sorted(_SUPPORTED_PROVIDERS)}"
            ),
            provider=resolved,
        )

    logger.debug("Creating embedding provider: %s", resolved)

    if resolved == "mock":
        return MockEmbeddingProvider(
            dims=settings.EMBEDDING_DIMENSIONS,
        )

    if resolved == "gemini":
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise EmbeddingConfigurationError(
                message=(
                    "GEMINI_API_KEY is not set. "
                    "Add it to your .env file or set EMBEDDING_PROVIDER=mock for testing."
                ),
                provider="gemini",
            )
        return GeminiEmbeddingProvider(
            api_key=api_key,
            model=settings.GEMINI_EMBEDDING_MODEL,
            dims=settings.EMBEDDING_DIMENSIONS,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )

    if resolved == "openai":
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise EmbeddingConfigurationError(
                message=(
                    "OPENAI_API_KEY is not set. "
                    "Add it to your .env file or set EMBEDDING_PROVIDER=mock for testing."
                ),
                provider="openai",
            )
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=settings.OPENAI_EMBEDDING_MODEL,
            dims=settings.OPENAI_EMBEDDING_DIMENSIONS,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )

    # Should be unreachable
    raise EmbeddingConfigurationError(
        message=f"Unhandled embedding provider '{resolved}'.",
        provider=resolved,
    )


def get_default_embedding_provider() -> BaseEmbeddingProvider:
    """
    Return the provider specified by the EMBEDDING_PROVIDER environment variable.

    Convenience wrapper around ``get_embedding_provider(None)``.
    """
    return get_embedding_provider(None)
