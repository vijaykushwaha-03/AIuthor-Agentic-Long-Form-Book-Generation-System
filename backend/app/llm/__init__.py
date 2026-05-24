"""
AIuthor Backend — LLM Provider Abstraction Package.

Public exports for the llm package.
Import from here rather than from submodules directly.
"""
from __future__ import annotations

from app.llm.schemas import LLMMessage, LLMRequest, LLMResponse, LLMProviderInfo
from app.llm.exceptions import LLMError, LLMConfigurationError, LLMProviderError
from app.llm.base import BaseLLMProvider
from app.llm.providers import GeminiLLMProvider, OpenAILLMProvider
from app.llm.factory import get_llm_provider, get_default_llm_provider

__all__ = [
    # Schemas
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "LLMProviderInfo",
    # Exceptions
    "LLMError",
    "LLMConfigurationError",
    "LLMProviderError",
    # Base
    "BaseLLMProvider",
    # Providers
    "GeminiLLMProvider",
    "OpenAILLMProvider",
    # Factory
    "get_llm_provider",
    "get_default_llm_provider",
]
