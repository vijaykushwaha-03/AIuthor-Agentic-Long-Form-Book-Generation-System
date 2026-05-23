"""
AIuthor Backend — Abstract LLM Provider Base Class.

All concrete providers (Gemini, OpenAI, Mock) inherit from BaseLLMProvider
and must implement `generate()`. The base class supplies shared helpers.
"""
from __future__ import annotations

import abc
import logging

from app.llm.schemas import LLMMessage, LLMProviderInfo, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class BaseLLMProvider(abc.ABC):
    """
    Abstract base class for all LLM provider implementations.

    Subclasses MUST implement:
        - provider_name (property)
        - model_name (property)
        - generate(request) -> LLMResponse
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

    @abc.abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Execute a generation request and return a normalised response.

        Args:
            request: Validated LLMRequest containing messages and options.

        Returns:
            LLMResponse with content and token metadata.

        Raises:
            LLMProviderError: On any runtime failure during the API call.
        """

    # ── Concrete helpers ──────────────────────────────────────────────────────

    def get_info(self) -> LLMProviderInfo:
        """
        Return provider capability metadata.

        Subclasses may override `configured` to reflect key availability.
        """
        return LLMProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            configured=True,       # Overridden by real providers when key may be absent
            supports_streaming=False,
        )

    @staticmethod
    def _messages_to_prompt(messages: list[LLMMessage]) -> str:
        """
        Flatten a message list into a single prompt string.

        Used by providers that accept a plain string rather than a structured
        chat format. System messages are prefixed with "[System]: ".

        Example output::

            [System]: You are a helpful writing assistant.
            User: Write a chapter outline.
        """
        parts: list[str] = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"[System]: {msg.content}")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}")
            else:  # assistant
                parts.append(f"Assistant: {msg.content}")
        return "\n".join(parts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name!r}, model={self.model_name!r})"
