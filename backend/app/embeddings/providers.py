"""
AIuthor Backend — Concrete Embedding Provider Implementations.

Two providers:
  - GeminiEmbeddingProvider — Google AI via google-genai SDK
  - OpenAIEmbeddingProvider — OpenAI via openai SDK

Real providers only instantiate SDK clients when embed() is called,
so they can be imported and introspected without network access.
"""
from __future__ import annotations

import logging
from typing import Any

from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.exceptions import EmbeddingConfigurationError, EmbeddingProviderError
from app.embeddings.schemas import (
    EmbeddingItem,
    EmbeddingProviderInfo,
    EmbeddingRequest,
    EmbeddingResponse,
)

logger = logging.getLogger(__name__)

# ── GeminiEmbeddingProvider ───────────────────────────────────────────────────

class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Google Gemini embedding provider using the google-genai SDK.

    Raises EmbeddingConfigurationError at instantiation if the API key is absent.
    The SDK client is created lazily inside embed() so the class can be
    instantiated and inspected in tests without a real network call.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
        dims: int = 768,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key or not api_key.strip():
            raise EmbeddingConfigurationError(
                message="Gemini API key is required but was not provided.",
                provider="gemini",
            )
        self._api_key = api_key
        self._model = model
        self._dimensions = dims
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Call the Gemini Embeddings API and return a normalised EmbeddingResponse."""
        try:
            from google import genai  # type: ignore[import]
            from google.genai import types as genai_types  # type: ignore[import]
        except ImportError as exc:
            raise EmbeddingProviderError(
                message="google-genai package is not installed. Run: pip install google-genai",
                provider="gemini",
            ) from exc

        model_to_use = request.model or self._model
        dims = request.dimensions or self._dimensions

        logger.debug(
            "GeminiEmbeddingProvider.embed: model=%s texts=%d dims=%d",
            model_to_use, len(request.texts), dims,
        )

        try:
            client = genai.Client(api_key=self._api_key)
            items: list[EmbeddingItem] = []

            for i, text in enumerate(request.texts):
                response = client.models.embed_content(
                    model=model_to_use,
                    contents=text,
                    config=genai_types.EmbedContentConfig(
                        output_dimensionality=dims,
                    ),
                )
                # Extract embedding vector safely
                try:
                    vector: list[float] = response.embeddings[0].values  # type: ignore[index]
                except (AttributeError, IndexError, TypeError):
                    raise EmbeddingProviderError(
                        message=f"Unexpected Gemini embedding response shape for text[{i}].",
                        provider="gemini",
                    )

                items.append(
                    EmbeddingItem(
                        text_index=i,
                        embedding=vector,
                        token_count=self._estimate_token_count(text),
                    )
                )

        except EmbeddingProviderError:
            raise
        except Exception as exc:
            raise EmbeddingProviderError(
                message=f"Gemini embedding API call failed: {exc}",
                provider="gemini",
                details={"error": str(exc)},
            ) from exc

        actual_dims = len(items[0].embedding) if items else dims

        return EmbeddingResponse(
            provider=self.provider_name,
            model=model_to_use,
            dimensions=actual_dims,
            items=items,
            metadata=request.metadata,
        )

    def get_info(self) -> EmbeddingProviderInfo:
        return EmbeddingProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            dimensions=self.dimensions,
            configured=bool(self._api_key),
            supports_batching=True,
        )


# ── OpenAIEmbeddingProvider ───────────────────────────────────────────────────

class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI embedding provider using the official openai SDK.

    Raises EmbeddingConfigurationError at instantiation if the API key is absent.
    The SDK client is created lazily inside embed().
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dims: int = 1536,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key or not api_key.strip():
            raise EmbeddingConfigurationError(
                message="OpenAI API key is required but was not provided.",
                provider="openai",
            )
        self._api_key = api_key
        self._model = model
        self._dimensions = dims
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Call the OpenAI Embeddings API and return a normalised EmbeddingResponse."""
        try:
            import openai  # type: ignore[import]
        except ImportError as exc:
            raise EmbeddingProviderError(
                message="openai package is not installed. Run: pip install openai",
                provider="openai",
            ) from exc

        model_to_use = request.model or self._model
        dims = request.dimensions or self._dimensions

        logger.debug(
            "OpenAIEmbeddingProvider.embed: model=%s texts=%d dims=%d",
            model_to_use, len(request.texts), dims,
        )

        try:
            client = openai.OpenAI(api_key=self._api_key, timeout=self._timeout_seconds)

            # Pass dimensions only if the model supports it (text-embedding-3-*)
            kwargs: dict[str, Any] = {
                "model": model_to_use,
                "input": request.texts,
            }
            if "text-embedding-3" in model_to_use:
                kwargs["dimensions"] = dims

            response = client.embeddings.create(**kwargs)  # type: ignore[arg-type]

        except Exception as exc:
            raise EmbeddingProviderError(
                message=f"OpenAI embedding API call failed: {exc}",
                provider="openai",
                details={"error": str(exc)},
            ) from exc

        # Build EmbeddingItems
        items: list[EmbeddingItem] = []
        try:
            for data_item in response.data:
                items.append(
                    EmbeddingItem(
                        text_index=data_item.index,
                        embedding=data_item.embedding,
                        token_count=None,  # Per-item token count not in OpenAI response
                    )
                )
        except (AttributeError, TypeError) as exc:
            raise EmbeddingProviderError(
                message=f"Unexpected OpenAI embedding response shape: {exc}",
                provider="openai",
            ) from exc

        actual_dims = len(items[0].embedding) if items else dims

        return EmbeddingResponse(
            provider=self.provider_name,
            model=model_to_use,
            dimensions=actual_dims,
            items=items,
            metadata=request.metadata,
        )

    def get_info(self) -> EmbeddingProviderInfo:
        return EmbeddingProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            dimensions=self.dimensions,
            configured=bool(self._api_key),
            supports_batching=True,
        )
