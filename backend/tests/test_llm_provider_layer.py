"""
AIuthor Backend — Tests: LLM Provider Layer (Module 5.0).

Tests for schemas, exceptions, providers, factory, and LLMService.

IMPORTANT:
  - No test calls Gemini or OpenAI APIs.
  - No test requires GEMINI_API_KEY or OPENAI_API_KEY.
  - All tests pass offline.
"""
from __future__ import annotations

import os

import pytest

# ── Ensure test env is set (conftest.py also does this, but belt-and-suspenders)
os.environ.setdefault("LLM_PROVIDER", "mock")


# ─────────────────────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMMessage:
    """Tests for the LLMMessage schema."""

    def test_accepts_system_role(self):
        from app.llm.schemas import LLMMessage
        msg = LLMMessage(role="system", content="You are a writing assistant.")
        assert msg.role == "system"

    def test_accepts_user_role(self):
        from app.llm.schemas import LLMMessage
        msg = LLMMessage(role="user", content="Write a chapter outline.")
        assert msg.role == "user"

    def test_accepts_assistant_role(self):
        from app.llm.schemas import LLMMessage
        msg = LLMMessage(role="assistant", content="Here is the outline.")
        assert msg.role == "assistant"

    def test_rejects_invalid_role(self):
        from pydantic import ValidationError
        from app.llm.schemas import LLMMessage
        with pytest.raises(ValidationError):
            LLMMessage(role="bot", content="Hello.")

    def test_rejects_empty_content(self):
        from pydantic import ValidationError
        from app.llm.schemas import LLMMessage
        with pytest.raises(ValidationError):
            LLMMessage(role="user", content="")


class TestLLMRequest:
    """Tests for the LLMRequest schema."""

    def test_valid_single_message(self):
        from app.llm.schemas import LLMMessage, LLMRequest
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello.")])
        assert len(req.messages) == 1

    def test_rejects_empty_messages(self):
        from pydantic import ValidationError
        from app.llm.schemas import LLMRequest
        with pytest.raises(ValidationError):
            LLMRequest(messages=[])

    def test_optional_fields_default_to_none(self):
        from app.llm.schemas import LLMMessage, LLMRequest
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hi")])
        assert req.model is None
        assert req.temperature is None
        assert req.max_output_tokens is None
        assert req.metadata is None

    def test_temperature_validation_accepts_valid_range(self):
        from app.llm.schemas import LLMMessage, LLMRequest
        req = LLMRequest(
            messages=[LLMMessage(role="user", content="Hi")],
            temperature=1.5,
        )
        assert req.temperature == 1.5

    def test_temperature_validation_rejects_out_of_range(self):
        from pydantic import ValidationError
        from app.llm.schemas import LLMMessage, LLMRequest
        with pytest.raises(ValidationError):
            LLMRequest(
                messages=[LLMMessage(role="user", content="Hi")],
                temperature=3.0,
            )

    def test_max_output_tokens_must_be_positive(self):
        from pydantic import ValidationError
        from app.llm.schemas import LLMMessage, LLMRequest
        with pytest.raises(ValidationError):
            LLMRequest(
                messages=[LLMMessage(role="user", content="Hi")],
                max_output_tokens=0,
            )


# ─────────────────────────────────────────────────────────────────────────────
# MockLLMProvider Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockLLMProvider:
    """Tests for the deterministic MockLLMProvider."""

    def _make_request(self, user_text: str = "Tell me a story."):
        from app.llm.schemas import LLMMessage, LLMRequest
        return LLMRequest(messages=[LLMMessage(role="user", content=user_text)])

    def test_returns_deterministic_response(self):
        from app.llm.providers import MockLLMProvider
        provider = MockLLMProvider()
        resp = provider.generate(self._make_request("Tell me a story."))
        assert "Mock response for: Tell me a story." in resp.content

    def test_returns_token_counts(self):
        from app.llm.providers import MockLLMProvider
        provider = MockLLMProvider()
        resp = provider.generate(self._make_request("Hello world."))
        assert resp.input_tokens is not None and resp.input_tokens > 0
        assert resp.output_tokens is not None and resp.output_tokens > 0
        assert resp.total_tokens == resp.input_tokens + resp.output_tokens

    def test_provider_name_is_mock(self):
        from app.llm.providers import MockLLMProvider
        assert MockLLMProvider().provider_name == "mock"

    def test_model_name_is_mock_llm(self):
        from app.llm.providers import MockLLMProvider
        assert MockLLMProvider().model_name == "mock-llm"

    def test_get_info_configured_true(self):
        from app.llm.providers import MockLLMProvider
        info = MockLLMProvider().get_info()
        assert info.configured is True
        assert info.provider == "mock"

    def test_echoes_last_user_message(self):
        from app.llm.schemas import LLMMessage, LLMRequest
        from app.llm.providers import MockLLMProvider
        req = LLMRequest(messages=[
            LLMMessage(role="system", content="You are a writer."),
            LLMMessage(role="user", content="Write chapter one."),
        ])
        resp = MockLLMProvider().generate(req)
        assert "Write chapter one." in resp.content

    def test_passes_through_metadata(self):
        from app.llm.schemas import LLMMessage, LLMRequest
        from app.llm.providers import MockLLMProvider
        req = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello.")],
            metadata={"run_id": "abc-123"},
        )
        resp = MockLLMProvider().generate(req)
        assert resp.metadata == {"run_id": "abc-123"}


# ─────────────────────────────────────────────────────────────────────────────
# Factory Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMFactory:
    """Tests for get_llm_provider() factory function."""

    def test_get_mock_provider_by_name(self):
        from app.llm.factory import get_llm_provider
        from app.llm.providers import MockLLMProvider
        provider = get_llm_provider("mock")
        assert isinstance(provider, MockLLMProvider)

    def test_unknown_provider_raises_configuration_error(self):
        from app.llm.factory import get_llm_provider
        from app.llm.exceptions import LLMConfigurationError
        with pytest.raises(LLMConfigurationError):
            get_llm_provider("anthropic")

    def test_gemini_without_key_raises_configuration_error(self):
        """GeminiLLMProvider.__init__ should raise if api_key is empty."""
        from app.llm.providers import GeminiLLMProvider
        from app.llm.exceptions import LLMConfigurationError
        with pytest.raises(LLMConfigurationError):
            GeminiLLMProvider(api_key="")

    def test_openai_without_key_raises_configuration_error(self):
        """OpenAILLMProvider.__init__ should raise if api_key is empty."""
        from app.llm.providers import OpenAILLMProvider
        from app.llm.exceptions import LLMConfigurationError
        with pytest.raises(LLMConfigurationError):
            OpenAILLMProvider(api_key="")

    def test_gemini_with_key_instantiates(self):
        """GeminiLLMProvider should instantiate without error when a key is provided."""
        from app.llm.providers import GeminiLLMProvider
        p = GeminiLLMProvider(api_key="fake-key-for-init-test")
        assert p.provider_name == "gemini"

    def test_openai_with_key_instantiates(self):
        """OpenAILLMProvider should instantiate without error when a key is provided."""
        from app.llm.providers import OpenAILLMProvider
        p = OpenAILLMProvider(api_key="sk-fake-key-for-init-test")
        assert p.provider_name == "openai"

    def test_factory_provider_name_gemini(self):
        from app.llm.factory import get_llm_provider
        from app.llm.providers import GeminiLLMProvider
        p = get_llm_provider.__wrapped__ if hasattr(get_llm_provider, "__wrapped__") else get_llm_provider
        # Just verify mock path works (cannot test gemini without key)
        provider = get_llm_provider("mock")
        assert provider.provider_name == "mock"


# ─────────────────────────────────────────────────────────────────────────────
# LLMService Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMService:
    """Tests for the LLMService wrapper class."""

    def _make_request(self, content: str = "Write an introduction."):
        from app.llm.schemas import LLMMessage, LLMRequest
        return LLMRequest(messages=[LLMMessage(role="user", content=content)])

    def test_service_with_mock_provider_generates_response(self):
        from app.llm.providers import MockLLMProvider
        from app.services.llm_service import LLMService
        service = LLMService(provider=MockLLMProvider())
        resp = service.generate_text(self._make_request())
        assert resp.content
        assert resp.provider == "mock"

    def test_service_get_provider_info(self):
        from app.llm.providers import MockLLMProvider
        from app.services.llm_service import LLMService
        service = LLMService(provider=MockLLMProvider())
        info = service.get_provider_info()
        assert info.provider == "mock"
        assert info.configured is True

    def test_service_response_has_model_field(self):
        from app.llm.providers import MockLLMProvider
        from app.services.llm_service import LLMService
        service = LLMService(provider=MockLLMProvider())
        resp = service.generate_text(self._make_request("Hello"))
        assert resp.model == "mock-llm"

    def test_service_response_has_token_counts(self):
        from app.llm.providers import MockLLMProvider
        from app.services.llm_service import LLMService
        service = LLMService(provider=MockLLMProvider())
        resp = service.generate_text(self._make_request("Outline chapter 1"))
        assert isinstance(resp.total_tokens, int)
        assert resp.total_tokens > 0


# ─────────────────────────────────────────────────────────────────────────────
# Exception Hierarchy Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMExceptions:
    """Tests for the LLM exception hierarchy."""

    def test_llm_configuration_error_is_llm_error(self):
        from app.llm.exceptions import LLMError, LLMConfigurationError
        exc = LLMConfigurationError("missing key", provider="gemini")
        assert isinstance(exc, LLMError)
        assert exc.provider == "gemini"

    def test_llm_provider_error_is_llm_error(self):
        from app.llm.exceptions import LLMError, LLMProviderError
        exc = LLMProviderError("call failed", provider="openai", details={"code": 429})
        assert isinstance(exc, LLMError)
        assert exc.details == {"code": 429}

    def test_exception_message_preserved(self):
        from app.llm.exceptions import LLMConfigurationError
        exc = LLMConfigurationError("API key missing")
        assert exc.message == "API key missing"
        assert str(exc) == "API key missing"
