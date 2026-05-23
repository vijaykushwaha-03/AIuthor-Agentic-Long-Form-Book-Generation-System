"""
AIuthor Backend — Abstract Embedding Provider Base Class.

All concrete providers (Gemini, OpenAI, Mock) inherit from BaseEmbeddingProvider
and must implement `embed()`. The base class supplies shared helpers.
"""
from __future__ import annotations

import abc
import logging

from app.embeddings.schemas import EmbeddingProviderInfo, EmbeddingRequest, EmbeddingResponse

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(abc.ABC):
    """
    Abstract base class for all embedding provider implementations.

    Subclasses MUST implement:
        - provider_name (property)
        - model_name (property)
        - dimensions (property)
        - embed(request) -> EmbeddingResponse
    """

    # ── Abstract interface ────────────────────────────────────────────────────

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return the canonical provider identifier (e.g. 'gemini')."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Return the default model name used by this provider instance."""

    @property
    @abc.abstractmethod
    def dimensions(self) -> int:
        """Return the default output vector dimensions for this provider."""

    @abc.abstractmethod
    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings for all texts in the request.

        Args:
            request: Validated EmbeddingRequest containing texts and options.

        Returns:
            EmbeddingResponse with one EmbeddingItem per input text.

        Raises:
            EmbeddingProviderError: On any runtime failure during the API call.
        """

    # ── Concrete helpers ──────────────────────────────────────────────────────

    def get_info(self) -> EmbeddingProviderInfo:
        """
        Return provider capability metadata.

        Subclasses may override `configured` to reflect key availability.
        """
        return EmbeddingProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            dimensions=self.dimensions,
            configured=True,
            supports_batching=True,
        )

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        """
        Rough token count estimate based on word count.

        Uses a simple word split as a proxy — accurate enough for logging/billing
        estimates without requiring a tokeniser dependency.

        Args:
            text: Input string.

        Returns:
            Approximate token count (word count × 1.3, rounded).
        """
        words = len(text.split())
        # Rough multiplier: English averages ~1.3 tokens per word
        return max(1, round(words * 1.3))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider={self.provider_name!r}, "
            f"model={self.model_name!r}, "
            f"dimensions={self.dimensions})"
        )
