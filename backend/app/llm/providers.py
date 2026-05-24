"""
AIuthor Backend — Concrete LLM Provider Implementations.

Two providers:
  - GeminiLLMProvider — Google AI via google-genai SDK
  - OpenAILLMProvider — OpenAI/GPT via openai SDK

Real providers only instantiate SDK clients when generate() is called,
so they can be imported and introspected without network access.

Rate limiting (GeminiLLMProvider):
  A module-level token-bucket limiter gates every generate_content call so
  we never exceed GEMINI_RPM requests per minute.  GEMINI_CONCURRENCY limits
  how many calls are in-flight at once (default 1 for sequential generation).

AFC (Automatic Function Calling):
  AFC is disabled by default for all prose-generation steps.  Only agents
  that explicitly set enable_tools=True (e.g. a future web-research agent)
  will have tool-calling active.  This eliminates the noisy
  "AFC is enabled with max remote calls: 10" log line on every chapter call.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMConfigurationError, LLMProviderError
from app.llm.schemas import LLMProviderInfo, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


# ── Gemini rate limiter ───────────────────────────────────────────────────────

class _GeminiRateLimiter:
    """
    Thread-safe token-bucket rate limiter for Gemini generate_content calls.

    - ``rpm``         : max requests per minute
    - ``concurrency`` : max simultaneous in-flight calls (semaphore)

    Usage::

        _limiter = _GeminiRateLimiter(rpm=3, concurrency=1)
        with _limiter:
            response = client.models.generate_content(...)
    """

    def __init__(self, rpm: int = 3, concurrency: int = 1) -> None:
        self._rpm = rpm
        self._interval = 60.0 / rpm          # seconds between tokens
        self._lock = threading.Lock()
        self._last_call_time: float = 0.0
        self._semaphore = threading.Semaphore(concurrency)

    def _wait_for_token(self) -> None:
        """Block until at least ``_interval`` seconds have passed since the last call."""
        with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_call_time)
            if wait > 0:
                logger.debug(
                    "_GeminiRateLimiter: throttling %.1fs to stay within %d RPM", wait, self._rpm
                )
                time.sleep(wait)
            self._last_call_time = time.monotonic()

    def __enter__(self) -> "_GeminiRateLimiter":
        self._semaphore.acquire()
        self._wait_for_token()
        return self

    def __exit__(self, *_: Any) -> None:
        self._semaphore.release()


# Module-level limiter instance — shared across all GeminiLLMProvider instances
# in the process.  Reconfigured via _configure_limiter() when provider is built.
_gemini_limiter: _GeminiRateLimiter = _GeminiRateLimiter(rpm=3, concurrency=1)
_limiter_lock = threading.Lock()


def _configure_limiter(rpm: int, concurrency: int) -> None:
    """Reconfigure the module-level Gemini rate limiter.  Thread-safe."""
    global _gemini_limiter
    with _limiter_lock:
        _gemini_limiter = _GeminiRateLimiter(rpm=rpm, concurrency=concurrency)
        logger.info(
            "GeminiRateLimiter configured: rpm=%d concurrency=%d", rpm, concurrency
        )


# ── GeminiLLMProvider ─────────────────────────────────────────────────────────


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini provider using the google-genai SDK.

    Key design decisions
    --------------------
    * AFC disabled by default (``enable_tools=False``): plain chapter-drafting,
      humanising, editing, and fact-checking calls never enable Automatic
      Function Calling.  Only agents that explicitly pass ``enable_tools=True``
      activate AFC.
    * Central rate limiter: every generate call passes through ``_gemini_limiter``
      which enforces GEMINI_RPM and GEMINI_CONCURRENCY *before* hitting the API.
    * Hard quota failure: if 429 RESOURCE_EXHAUSTED persists after all retries
      the method raises ``LLMProviderError`` with a clear user-facing message.
      It never silently falls back to mock content.

    Raises LLMConfigurationError at instantiation time if the API key is absent.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_output_tokens: int = 4000,
        timeout_seconds: int = 60,
        enable_tools: bool = False,
        rpm: int = 3,
        concurrency: int = 1,
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
        self._enable_tools = enable_tools

        # Reconfigure the module-level limiter with our settings.
        # If multiple providers are created with different RPM values the last
        # one wins — this is acceptable for a single-provider deployment.
        _configure_limiter(rpm, concurrency)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Call the Gemini API and return a normalised LLMResponse.

        Flow
        ----
        1. Acquire rate-limiter slot (blocks if needed to stay within RPM limit).
        2. Build GenerateContentConfig with AFC disabled (unless enable_tools=True).
        3. Call SDK with up to ``max_retries`` retries on 429 RESOURCE_EXHAUSTED.
        4. On quota exhaustion after all retries: raise LLMProviderError with a
           clear "Gemini quota exhausted" message — no mock fallback.
        """
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
            "GeminiLLMProvider.generate: model=%s temperature=%.2f max_tokens=%d tools=%s",
            model_to_use, temperature, max_tokens, self._enable_tools,
        )

        import re

        # ── Build GenerateContentConfig ───────────────────────────────────────
        #
        # When enable_tools is False (the default for all prose-generation nodes)
        # we disable AFC completely. The SDK emits a warning if disable=True but
        # maximum_remote_calls is still the SDK default of 10 — so we set BOTH
        # disable=True AND maximum_remote_calls=0 to make both fields consistent
        # and fully silence the warning:
        #   "automatic_function_calling.disable is set to True. But
        #    automatic_function_calling.maximum_remote_calls is set to 10."
        #
        if self._enable_tools:
            gen_config = genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        else:
            try:
                # google-genai ≥ 0.8 exposes AutomaticFunctionCallingConfig.
                # Setting BOTH disable=True AND maximum_remote_calls=0 prevents
                # the SDK "conflicting settings" warning.
                afc_config = genai_types.AutomaticFunctionCallingConfig(
                    disable=True,
                    maximum_remote_calls=0,
                )
                gen_config = genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    automatic_function_calling=afc_config,
                )
            except (AttributeError, TypeError):
                # Older SDK version — fall back to config without AFC field
                gen_config = genai_types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

        # ── Retry loop ────────────────────────────────────────────────────────
        max_retries = 3           # 3 retries max; each 429 waits ~60s so 3×60 = ~3min
        default_retry_delay = 20
        response = None

        for attempt in range(max_retries):
            try:
                # Pre-throttle: block until rate-limiter allows the call
                with _gemini_limiter:
                    client = genai.Client(api_key=self._api_key)
                    response = client.models.generate_content(
                        model=model_to_use,
                        contents=prompt,
                        config=gen_config,
                    )
                break  # success

            except Exception as exc:
                exc_str = str(exc)
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    delay = default_retry_delay

                    # Try to parse retry delay from API response
                    match = re.search(
                        r'retry in\s+([0-9\.]+)\s*s', exc_str, re.IGNORECASE
                    )
                    if match:
                        try:
                            delay = int(float(match.group(1))) + 2
                        except Exception:
                            pass
                    else:
                        match2 = re.search(
                            r"retryDelay['\"]?\s*:\s*['\"]?([0-9]+)['\"]?\s*s?",
                            exc_str, re.IGNORECASE,
                        )
                        if match2:
                            try:
                                delay = int(match2.group(1)) + 2
                            except Exception:
                                pass

                    if attempt < max_retries - 1:
                        logger.warning(
                            "Gemini API rate limited (429 RESOURCE_EXHAUSTED). "
                            "Retrying in %ds (Attempt %d/%d)...",
                            delay, attempt + 1, max_retries,
                        )
                        time.sleep(delay)
                    else:
                        # All retries exhausted — fail clearly, no mock fallback
                        quota_msg = (
                            "Gemini quota exhausted after all retries. "
                            "Real AI export stopped. "
                            "Retry later, reduce GEMINI_RPM in .env, "
                            "or wait for your daily quota to reset.\n"
                            f"Original error: {exc}"
                        )
                        logger.error("GeminiLLMProvider: %s", quota_msg)
                        raise LLMProviderError(
                            message=quota_msg,
                            provider="gemini",
                            details={"error": str(exc), "attempts": max_retries},
                        ) from exc
                else:
                    raise LLMProviderError(
                        message=f"Gemini API call failed: {exc}",
                        provider="gemini",
                        details={"error": str(exc)},
                    ) from exc

        # ── Extract text safely — response structure may vary ─────────────────
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
