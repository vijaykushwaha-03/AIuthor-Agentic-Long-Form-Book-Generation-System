"""
AIuthor Backend — LLM Provider Status.

Endpoints:
  GET  /api/llm/providers          — List supported providers
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.llm.exceptions import LLMConfigurationError, LLMProviderError
from app.llm.factory import get_llm_provider
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
        "it is properly configured (i.e. the required API key is present)."
    ),
)
def get_provider_info() -> LLMProviderInfo:
    """Return current provider metadata without calling the model."""
    from app.config import get_settings
    settings = get_settings()

    provider_name = settings.LLM_PROVIDER

    # Determine 'configured' without instantiating a real provider
    # (avoids raising LLMConfigurationError if key is missing)
    if provider_name == "gemini":
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


