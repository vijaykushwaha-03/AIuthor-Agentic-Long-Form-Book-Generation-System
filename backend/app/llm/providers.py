"""
AIuthor Backend — Concrete LLM Provider Implementations.

Three providers:
  - MockLLMProvider   — deterministic, no external calls (used in tests)
  - GeminiLLMProvider — Google AI via google-genai SDK
  - OpenAILLMProvider — OpenAI/GPT via openai SDK

Real providers only instantiate SDK clients when generate() is called,
so they can be imported and introspected without network access.
"""
from __future__ import annotations

import logging
from typing import Any

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMConfigurationError, LLMProviderError
from app.llm.schemas import LLMProviderInfo, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


# ── MockLLMProvider ───────────────────────────────────────────────────────────

class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic provider for tests and local development.

    - Makes no external network calls.
    - Always returns a predictable response derived from the last user message.
    - Token counts are approximated using word count.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-llm"

    def generate(self, request: LLMRequest) -> LLMResponse:
        # Find the last user message to echo back
        last_user_content = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_content = msg.content
                break

        content = f"Mock response for: {last_user_content}"

        # Approximate token counts using word count (rough but consistent)
        prompt_text = self._messages_to_prompt(request.messages)
        input_tokens = len(prompt_text.split())
        output_tokens = len(content.split())

        logger.debug("MockLLMProvider.generate called, returning deterministic response.")

        return LLMResponse(
            provider=self.provider_name,
            model=self.model_name,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            metadata=request.metadata,
        )

    def get_info(self) -> LLMProviderInfo:
        return LLMProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            configured=True,   # Mock is always "configured"
            supports_streaming=False,
        )


# ── GeminiLLMProvider ─────────────────────────────────────────────────────────

class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini provider using the google-genai SDK.

    Raises LLMConfigurationError at instantiation time if the API key is
    absent. The SDK client is created lazily inside generate() so the class
    can be instantiated and inspected in tests without a real network call,
    as long as generate() is not actually invoked.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_output_tokens: int = 4000,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMConfigurationError(
                message="Gemini API key is required but was not provided.",
                provider="gemini",
            )
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Call the Gemini API and return a normalised LLMResponse."""
        try:
            from google import genai  # type: ignore[import]
            from google.genai import types as genai_types  # type: ignore[import]
        except ImportError as exc:
            raise LLMProviderError(
                message="google-genai package is not installed. Run: pip install google-genai",
                provider="gemini",
            ) from exc

        model_to_use = request.model or self._model
        temperature = request.temperature if request.temperature is not None else self._temperature
        max_tokens = request.max_output_tokens or self._max_output_tokens

        # Build the prompt as a plain string (Gemini supports multi-turn natively
        # but we use the simple string interface for maximum compatibility)
        prompt = self._messages_to_prompt(request.messages)

        logger.debug(
            "GeminiLLMProvider.generate: model=%s temperature=%.2f max_tokens=%d",
            model_to_use, temperature, max_tokens,
        )

        try:
            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=model_to_use,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
        except Exception as exc:
            raise LLMProviderError(
                message=f"Gemini API call failed: {exc}",
                provider="gemini",
                details={"error": str(exc)},
            ) from exc

        # Extract text safely — response structure may vary
        try:
            content = response.text or ""
        except Exception:
            content = ""

        # Extract token usage safely
        input_tokens: int | None = None
        output_tokens: int | None = None
        total_tokens: int | None = None
        try:
            usage = response.usage_metadata
            if usage:
                input_tokens = getattr(usage, "prompt_token_count", None)
                output_tokens = getattr(usage, "candidates_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)
        except Exception:
            pass  # Token counts are optional; do not crash

        return LLMResponse(
            provider=self.provider_name,
            model=model_to_use,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            metadata=request.metadata,
        )

    def get_info(self) -> LLMProviderInfo:
        return LLMProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            configured=bool(self._api_key),
            supports_streaming=False,
        )


# ── OpenAILLMProvider ─────────────────────────────────────────────────────────

class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI / GPT provider using the official openai SDK.

    Raises LLMConfigurationError at instantiation time if the API key is
    absent. The SDK client is created lazily inside generate().
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_output_tokens: int = 4000,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMConfigurationError(
                message="OpenAI API key is required but was not provided.",
                provider="openai",
            )
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Call the OpenAI API and return a normalised LLMResponse."""
        try:
            import openai  # type: ignore[import]
        except ImportError as exc:
            raise LLMProviderError(
                message="openai package is not installed. Run: pip install openai",
                provider="openai",
            ) from exc

        model_to_use = request.model or self._model
        temperature = request.temperature if request.temperature is not None else self._temperature
        max_tokens = request.max_output_tokens or self._max_output_tokens

        # Convert LLMMessages to OpenAI chat format
        messages: list[dict[str, Any]] = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        logger.debug(
            "OpenAILLMProvider.generate: model=%s temperature=%.2f max_tokens=%d",
            model_to_use, temperature, max_tokens,
        )

        try:
            client = openai.OpenAI(api_key=self._api_key, timeout=self._timeout_seconds)
            completion = client.chat.completions.create(
                model=model_to_use,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            raise LLMProviderError(
                message=f"OpenAI API call failed: {exc}",
                provider="openai",
                details={"error": str(exc)},
            ) from exc

        # Extract content safely
        try:
            content = completion.choices[0].message.content or ""
        except (IndexError, AttributeError):
            content = ""

        # Extract token usage safely
        input_tokens: int | None = None
        output_tokens: int | None = None
        total_tokens: int | None = None
        try:
            usage = completion.usage
            if usage:
                input_tokens = getattr(usage, "prompt_tokens", None)
                output_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
        except Exception:
            pass

        return LLMResponse(
            provider=self.provider_name,
            model=model_to_use,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            metadata=request.metadata,
        )

    def get_info(self) -> LLMProviderInfo:
        return LLMProviderInfo(
            provider=self.provider_name,
            model=self.model_name,
            configured=bool(self._api_key),
            supports_streaming=False,
        )
