"""
AIuthor Backend — Embedding Service Wrapper.

EmbeddingService is the single entry-point that business logic (and later,
the chunk embedding job) should use when generating embeddings. It wraps a
provider and provides a stable interface for observability and DB-persistence
hooks to be injected in Module 6.0B without changing provider code.
"""
from __future__ import annotations

import logging

from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.factory import get_default_embedding_provider
from app.embeddings.schemas import EmbeddingProviderInfo, EmbeddingRequest, EmbeddingResponse

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Thin service wrapper around a BaseEmbeddingProvider.

    Responsible for:
    - Delegating embedding requests to the configured provider.
    - Providing a stable API surface for future observability and DB-write
      hooks without touching provider implementations.

    Usage::

        service = EmbeddingService()                              # uses env default
    """

    def __init__(self, provider: BaseEmbeddingProvider | None = None) -> None:
        self.provider: BaseEmbeddingProvider = provider or get_default_embedding_provider()

    # ── Public methods ────────────────────────────────────────────────────────

    def embed_texts(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Send an embedding request to the underlying provider.

        Future: will persist embedding vectors to DocumentChunk rows in Module 6.0B.

        Args:
            request: Validated EmbeddingRequest.

        Returns:
            EmbeddingResponse from the provider.

        Raises:
            EmbeddingProviderError: If the underlying provider call fails.
        """
        logger.debug(
            "EmbeddingService.embed_texts: provider=%s texts=%d",
            self.provider.provider_name,
            len(request.texts),
        )
        response = self.provider.embed(request)
        logger.debug(
            "EmbeddingService.embed_texts: completed dims=%d items=%d",
            response.dimensions,
            len(response.items),
        )
        return response

    def get_provider_info(self) -> EmbeddingProviderInfo:
        """
        Return capability metadata for the active provider.

        Returns:
            EmbeddingProviderInfo with provider name, model, dimensions, and configured flag.
        """
        return self.provider.get_info()
