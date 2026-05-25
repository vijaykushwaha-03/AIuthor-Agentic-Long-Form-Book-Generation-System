"""
AIuthor Backend — LLM Provider Factory.

Resolves the configured LLM provider and returns an instantiated
BaseLLMProvider ready for use. Providers are created on demand —
never at app startup — so missing API keys don't block the server.
"""
from __future__ import annotations

import logging

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMConfigurationError
from app.llm.providers import GeminiLLMProvider, OpenAILLMProvider, NvidiaLLMProvider

logger = logging.getLogger(__name__)

_SUPPORTED_PROVIDERS = {"gemini", "openai", "nvidia"}


def get_llm_provider(provider: str | None = None) -> BaseLLMProvider:
    """
    Instantiate and return the requested LLM provider.

    Resolution order:
      1. ``provider`` argument (if given)
      2. ``settings.LLM_PROVIDER`` environment variable
      3. Falls back to ``"gemini"`` (built-in default)

    Args:
        provider: Explicit provider name override.  One of
                  ``"gemini"``, ``"openai"``, or ``"mock"``.

    Returns:
        A fully configured BaseLLMProvider instance.

    Raises:
        LLMConfigurationError: If the provider name is unknown, or if a
            real provider's API key is missing.
    """
    from app.config import get_settings
    settings = get_settings()

    resolved = (provider or settings.LLM_PROVIDER or "gemini").lower()

    if resolved not in _SUPPORTED_PROVIDERS:
        raise LLMConfigurationError(
            message=(
                f"Unknown LLM provider '{resolved}'. "
                f"Supported providers: {sorted(_SUPPORTED_PROVIDERS)}"
            ),
            provider=resolved,
        )

    logger.debug("Creating LLM provider: %s", resolved)

    if resolved == "gemini":
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise LLMConfigurationError(
                message=(
                    "GEMINI_API_KEY is not set. "
                    "Add GEMINI_API_KEY to your .env file."
                ),
                provider="gemini",
            )
        return GeminiLLMProvider(
            api_key=api_key,
            model=settings.GEMINI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            enable_tools=False,           # AFC disabled for all prose generation
            rpm=settings.GEMINI_RPM,
            concurrency=settings.GEMINI_CONCURRENCY,
        )

    if resolved == "openai":
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise LLMConfigurationError(
                message=(
                    "OPENAI_API_KEY is not set. "
                    "Add OPENAI_API_KEY to your .env file."
                ),
                provider="openai",
            )
        return OpenAILLMProvider(
            api_key=api_key,
            model=settings.OPENAI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )

    if resolved == "nvidia":
        api_key = settings.NVIDIA_API_KEY
        if not api_key:
            raise LLMConfigurationError(
                message=(
                    "NVIDIA_API_KEY is not set. "
                    "Add NVIDIA_API_KEY to your .env file."
                ),
                provider="nvidia",
            )
        return NvidiaLLMProvider(
            api_key=api_key,
            model=settings.NVIDIA_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        )

    # Should be unreachable — guarded by the set check above
    raise LLMConfigurationError(
        message=f"Unhandled provider '{resolved}'.",
        provider=resolved,
    )


def get_default_llm_provider() -> BaseLLMProvider:
    """
    Return the provider specified by the LLM_PROVIDER environment variable.

    Convenience wrapper around ``get_llm_provider(None)``.
    """
    return get_llm_provider(None)
