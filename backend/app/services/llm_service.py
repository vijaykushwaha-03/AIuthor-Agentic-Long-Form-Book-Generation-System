"""
AIuthor Backend — LLM Service Wrapper.

LLMService is the single entry-point that business logic (and later,
agent workflows) should use when calling an LLM. It wraps a provider
and provides a clean interface for observability hooks to be injected
in later modules without changing provider implementations.
"""
from __future__ import annotations

import logging

from app.llm.base import BaseLLMProvider
from app.llm.factory import get_default_llm_provider
from app.llm.schemas import LLMProviderInfo, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class LLMService:
    """
    Thin service wrapper around a BaseLLMProvider.

    Responsible for:
    - Delegating generation requests to the configured provider.
    - Providing a stable API surface for future observability hooks
      (DB logging, cost tracking) without touching provider code.

    Usage::

        service = LLMService()                      # uses default provider from env
        service = LLMService(provider=MockLLMProvider())  # inject for tests
    """

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self.provider: BaseLLMProvider = provider or get_default_llm_provider()

    # ── Public methods ────────────────────────────────────────────────────────

    def generate_text(self, request: LLMRequest) -> LLMResponse:
        """
        Send a generation request to the underlying provider.

        Future: will emit a PromptLog record after the call completes.

        Args:
            request: Validated LLMRequest.

        Returns:
            LLMResponse from the provider.

        Raises:
            LLMProviderError: If the underlying provider call fails.
        """
        logger.debug(
            "LLMService.generate_text: provider=%s messages=%d",
            self.provider.provider_name,
            len(request.messages),
        )
        response = self.provider.generate(request)
        logger.debug(
            "LLMService.generate_text: completed input_tokens=%s output_tokens=%s",
            response.input_tokens,
            response.output_tokens,
        )
        return response

    def get_provider_info(self) -> LLMProviderInfo:
        """
        Return capability metadata for the active provider.

        Returns:
            LLMProviderInfo with provider name, model, and configured flag.
        """
        return self.provider.get_info()
