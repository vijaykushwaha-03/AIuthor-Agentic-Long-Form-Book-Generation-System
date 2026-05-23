"""
AIuthor Backend — LLM Provider Status & Mock-Generation Routes.

Endpoints:
  GET  /api/llm/provider          — return current provider metadata
  POST /api/llm/mock-generate     — run generation via MockLLMProvider only

Important:
  - No endpoint here calls a real Gemini or OpenAI API.
  - Real LLM calls will be added inside agent/workflow modules (Module 6+).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.llm.exceptions import LLMConfigurationError, LLMProviderError
from app.llm.factory import get_llm_provider
from app.llm.providers import MockLLMProvider
from app.llm.schemas import LLMProviderInfo, LLMRequest, LLMResponse
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


# ── GET /api/llm/provider ─────────────────────────────────────────────────────

@router.get(
    "/provider",
    response_model=LLMProviderInfo,
    summary="LLM provider status",
    description=(
        "Returns the currently configured LLM provider name, model, and whether "
        "it is properly configured (i.e. the required API key is present or the "
        "provider is mock). Does not make any model API calls."
    ),
)
def get_provider_info() -> LLMProviderInfo:
    """Return current provider metadata without calling the model."""
    from app.config import get_settings
    settings = get_settings()

    provider_name = settings.LLM_PROVIDER

    # Determine 'configured' without instantiating a real provider
    # (avoids raising LLMConfigurationError if key is missing)
    if provider_name == "mock":
        model = "mock-llm"
        configured = True
    elif provider_name == "gemini":
        model = settings.GEMINI_MODEL
        configured = bool(settings.GEMINI_API_KEY)
    elif provider_name == "openai":
        model = settings.OPENAI_MODEL
        configured = bool(settings.OPENAI_API_KEY)
    else:
        # Unknown provider — still return info rather than crashing
        model = "unknown"
        configured = False

    return LLMProviderInfo(
        provider=provider_name,
        model=model,
        configured=configured,
        supports_streaming=False,
    )


# ── POST /api/llm/mock-generate ───────────────────────────────────────────────

@router.post(
    "/mock-generate",
    response_model=LLMResponse,
    status_code=status.HTTP_200_OK,
    summary="Mock LLM generation (test only)",
    description=(
        "Uses the configured LLM_PROVIDER (Gemini/OpenAI or Mock fallback) "
        "to generate text. Convenient for testing connection to real providers."
    ),
)
def mock_generate(request: LLMRequest) -> LLMResponse:
    """Run generation through the configured LLM provider."""
    try:
        provider = get_llm_provider()
        service = LLMService(provider=provider)
        return service.generate_text(request)
    except LLMConfigurationError as exc:
        logger.error("LLM configuration error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "llm_configuration_error", "message": exc.message},
        ) from exc
    except LLMProviderError as exc:
        logger.error("LLM provider error: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "llm_provider_error", "message": exc.message},
        ) from exc
