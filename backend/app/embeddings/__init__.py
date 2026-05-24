"""
AIuthor Backend — Embedding Provider Package.

Public re-exports for the embeddings package.
Import from here rather than from submodules directly.
"""
from __future__ import annotations

from app.embeddings.schemas import (
    EmbeddingRequest,
    EmbeddingItem,
    EmbeddingResponse,
    EmbeddingProviderInfo,
)
from app.embeddings.exceptions import (
    EmbeddingError,
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.providers import (
    GeminiEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.embeddings.factory import get_embedding_provider, get_default_embedding_provider

__all__ = [
    # Schemas
    "EmbeddingRequest",
    "EmbeddingItem",
    "EmbeddingResponse",
    "EmbeddingProviderInfo",
    # Exceptions
    "EmbeddingError",
    "EmbeddingConfigurationError",
    "EmbeddingProviderError",
    # Base
    "BaseEmbeddingProvider",
    # Providers
    "GeminiEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    # Factory
    "get_embedding_provider",
    "get_default_embedding_provider",
]
