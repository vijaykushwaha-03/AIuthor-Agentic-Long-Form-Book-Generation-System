"""
AIuthor Backend — Embedding Provider Status & Mock Routes.

Endpoints:
  GET  /api/embeddings/provider  — return current embedding provider metadata
  POST /api/embeddings/mock      — run embedding via MockEmbeddingProvider only

Important:
  - No endpoint here calls a real Gemini or OpenAI API.
  - Real embedding generation for DocumentChunk rows will be added in Module 6.0B.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.embeddings.exceptions import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.providers import MockEmbeddingProvider
from app.embeddings.schemas import EmbeddingProviderInfo, EmbeddingRequest, EmbeddingResponse
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


# ── GET /api/embeddings/provider ──────────────────────────────────────────────

@router.get(
    "/provider",
    response_model=EmbeddingProviderInfo,
    summary="Embedding provider status",
    description=(
        "Returns the currently configured embedding provider name, model, dimensions, "
        "and whether it is properly configured (i.e. the required API key is present "
        "or the provider is mock). Does not generate any embeddings."
    ),
)
def get_provider_info() -> EmbeddingProviderInfo:
    """Return current embedding provider metadata without calling the model."""
    from app.config import get_settings
    settings = get_settings()

    provider_name = settings.EMBEDDING_PROVIDER

    if provider_name == "mock":
        model = "mock-embedding"
        dims = settings.EMBEDDING_DIMENSIONS
        configured = True
    elif provider_name == "gemini":
        model = settings.GEMINI_EMBEDDING_MODEL
        dims = settings.EMBEDDING_DIMENSIONS
        configured = bool(settings.GEMINI_API_KEY)
    elif provider_name == "openai":
        model = settings.OPENAI_EMBEDDING_MODEL
        dims = settings.OPENAI_EMBEDDING_DIMENSIONS
        configured = bool(settings.OPENAI_API_KEY)
    else:
        model = "unknown"
        dims = 0
        configured = False

    return EmbeddingProviderInfo(
        provider=provider_name,
        model=model,
        dimensions=dims,
        configured=configured,
        supports_batching=True,
    )


# ── POST /api/embeddings/mock ─────────────────────────────────────────────────

@router.post(
    "/mock",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Mock embedding generation (test only)",
    description=(
        "Always uses MockEmbeddingProvider regardless of the configured EMBEDDING_PROVIDER. "
        "Returns deterministic hash-based vectors. "
        "Use this endpoint to validate the API contract without any real API calls."
    ),
)
def mock_embed(request: EmbeddingRequest) -> EmbeddingResponse:
    """Run embedding through MockEmbeddingProvider only. Never calls Gemini or OpenAI."""
    from app.config import get_settings
    settings = get_settings()

    try:
        service = EmbeddingService(
            provider=MockEmbeddingProvider(dims=settings.EMBEDDING_DIMENSIONS)
        )
        return service.embed_texts(request)
    except EmbeddingConfigurationError as exc:
        logger.error("Embedding configuration error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "embedding_configuration_error", "message": exc.message},
        ) from exc
    except EmbeddingProviderError as exc:
        logger.error("Embedding provider error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "embedding_provider_error", "message": exc.message},
        ) from exc
