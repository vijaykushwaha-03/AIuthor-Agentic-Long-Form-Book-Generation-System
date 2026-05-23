"""
AIuthor Backend — Tests: Embedding Provider Layer (Module 6.0A).

Tests for schemas, exceptions, providers, factory, and EmbeddingService.

IMPORTANT:
  - No test calls Gemini or OpenAI APIs.
  - No test requires GEMINI_API_KEY or OPENAI_API_KEY.
  - All tests pass offline.
"""
from __future__ import annotations

import os

import pytest

# Ensure test env is set (conftest.py also does this)
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("EMBEDDING_DIMENSIONS", "8")


# ─────────────────────────────────────────────────────────────────────────────
# Schema Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbeddingRequest:
    """Tests for the EmbeddingRequest schema."""

    def test_accepts_valid_single_text(self):
        from app.embeddings.schemas import EmbeddingRequest
        req = EmbeddingRequest(texts=["Hello world."])
        assert len(req.texts) == 1

    def test_accepts_multiple_texts(self):
        from app.embeddings.schemas import EmbeddingRequest
        req = EmbeddingRequest(texts=["First text.", "Second text.", "Third text."])
        assert len(req.texts) == 3

    def test_rejects_empty_texts_list(self):
        from pydantic import ValidationError
        from app.embeddings.schemas import EmbeddingRequest
        with pytest.raises(ValidationError):
            EmbeddingRequest(texts=[])

    def test_rejects_empty_string_in_texts(self):
        from pydantic import ValidationError
        from app.embeddings.schemas import EmbeddingRequest
        with pytest.raises(ValidationError):
            EmbeddingRequest(texts=["valid text", ""])

    def test_rejects_whitespace_only_string(self):
        from pydantic import ValidationError
        from app.embeddings.schemas import EmbeddingRequest
        with pytest.raises(ValidationError):
            EmbeddingRequest(texts=["   "])

    def test_rejects_invalid_dimensions(self):
        from pydantic import ValidationError
        from app.embeddings.schemas import EmbeddingRequest
        with pytest.raises(ValidationError):
            EmbeddingRequest(texts=["valid"], dimensions=0)

    def test_optional_fields_default_to_none(self):
        from app.embeddings.schemas import EmbeddingRequest
        req = EmbeddingRequest(texts=["Hello."])
        assert req.model is None
        assert req.dimensions is None
        assert req.metadata is None

    def test_accepts_positive_dimensions(self):
        from app.embeddings.schemas import EmbeddingRequest
        req = EmbeddingRequest(texts=["Hello."], dimensions=512)
        assert req.dimensions == 512


class TestEmbeddingItem:
    """Tests for the EmbeddingItem schema."""

    def test_valid_item(self):
        from app.embeddings.schemas import EmbeddingItem
        item = EmbeddingItem(text_index=0, embedding=[0.1, 0.2, 0.3])
        assert item.text_index == 0
        assert len(item.embedding) == 3

    def test_rejects_negative_text_index(self):
        from pydantic import ValidationError
        from app.embeddings.schemas import EmbeddingItem
        with pytest.raises(ValidationError):
            EmbeddingItem(text_index=-1, embedding=[0.1])

    def test_rejects_empty_embedding(self):
        from pydantic import ValidationError
        from app.embeddings.schemas import EmbeddingItem
        with pytest.raises(ValidationError):
            EmbeddingItem(text_index=0, embedding=[])


# ─────────────────────────────────────────────────────────────────────────────
# MockEmbeddingProvider Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockEmbeddingProvider:
    """Tests for the deterministic MockEmbeddingProvider."""

    def _provider(self, dims: int = 8):
        from app.embeddings.providers import MockEmbeddingProvider
        return MockEmbeddingProvider(dims=dims)

    def _request(self, texts: list[str] | None = None):
        from app.embeddings.schemas import EmbeddingRequest
        return EmbeddingRequest(texts=texts or ["Hello world."])

    def test_returns_correct_provider_name(self):
        assert self._provider().provider_name == "mock"

    def test_returns_correct_model_name(self):
        assert self._provider().model_name == "mock-embedding"

    def test_returns_correct_dimensions(self):
        assert self._provider(dims=16).dimensions == 16

    def test_embedding_length_equals_dimensions(self):
        provider = self._provider(dims=8)
        resp = provider.embed(self._request())
        assert len(resp.items[0].embedding) == 8

    def test_different_dims_setting_honoured(self):
        provider = self._provider(dims=32)
        resp = provider.embed(self._request())
        assert len(resp.items[0].embedding) == 32

    def test_same_text_produces_same_vector(self):
        provider = self._provider(dims=8)
        req = self._request(["Deterministic text for testing."])
        r1 = provider.embed(req)
        r2 = provider.embed(req)
        assert r1.items[0].embedding == r2.items[0].embedding

    def test_different_texts_produce_different_vectors(self):
        provider = self._provider(dims=8)
        from app.embeddings.schemas import EmbeddingRequest
        req = EmbeddingRequest(texts=["First sentence.", "Completely different content xyz."])
        resp = provider.embed(req)
        assert resp.items[0].embedding != resp.items[1].embedding

    def test_response_provider_is_mock(self):
        resp = self._provider().embed(self._request())
        assert resp.provider == "mock"

    def test_response_model_is_mock_embedding(self):
        resp = self._provider().embed(self._request())
        assert resp.model == "mock-embedding"

    def test_response_dimensions_matches(self):
        resp = self._provider(dims=8).embed(self._request())
        assert resp.dimensions == 8

    def test_multiple_texts_return_multiple_items(self):
        from app.embeddings.schemas import EmbeddingRequest
        provider = self._provider()
        req = EmbeddingRequest(texts=["First.", "Second.", "Third."])
        resp = provider.embed(req)
        assert len(resp.items) == 3

    def test_items_have_correct_text_indices(self):
        from app.embeddings.schemas import EmbeddingRequest
        provider = self._provider()
        req = EmbeddingRequest(texts=["A.", "B.", "C."])
        resp = provider.embed(req)
        assert [item.text_index for item in resp.items] == [0, 1, 2]

    def test_token_count_is_set(self):
        resp = self._provider().embed(self._request(["Hello world."]))
        assert resp.items[0].token_count is not None
        assert resp.items[0].token_count > 0

    def test_passes_through_metadata(self):
        from app.embeddings.schemas import EmbeddingRequest
        provider = self._provider()
        req = EmbeddingRequest(texts=["Hi."], metadata={"chunk_id": "abc-123"})
        resp = provider.embed(req)
        assert resp.metadata == {"chunk_id": "abc-123"}

    def test_get_info_configured_true(self):
        info = self._provider().get_info()
        assert info.configured is True
        assert info.provider == "mock"
        assert info.supports_batching is True


# ─────────────────────────────────────────────────────────────────────────────
# Factory Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbeddingFactory:
    """Tests for get_embedding_provider() factory function."""

    def test_get_mock_provider_by_name(self):
        from app.embeddings.factory import get_embedding_provider
        from app.embeddings.providers import MockEmbeddingProvider
        provider = get_embedding_provider("mock")
        assert isinstance(provider, MockEmbeddingProvider)

    def test_unknown_provider_raises_configuration_error(self):
        from app.embeddings.factory import get_embedding_provider
        from app.embeddings.exceptions import EmbeddingConfigurationError
        with pytest.raises(EmbeddingConfigurationError):
            get_embedding_provider("cohere")

    def test_gemini_without_key_raises_configuration_error(self):
        from app.embeddings.providers import GeminiEmbeddingProvider
        from app.embeddings.exceptions import EmbeddingConfigurationError
        with pytest.raises(EmbeddingConfigurationError):
            GeminiEmbeddingProvider(api_key="")

    def test_openai_without_key_raises_configuration_error(self):
        from app.embeddings.providers import OpenAIEmbeddingProvider
        from app.embeddings.exceptions import EmbeddingConfigurationError
        with pytest.raises(EmbeddingConfigurationError):
            OpenAIEmbeddingProvider(api_key="")

    def test_gemini_with_key_instantiates(self):
        from app.embeddings.providers import GeminiEmbeddingProvider
        p = GeminiEmbeddingProvider(api_key="fake-key-for-init-test")
        assert p.provider_name == "gemini"

    def test_openai_with_key_instantiates(self):
        from app.embeddings.providers import OpenAIEmbeddingProvider
        p = OpenAIEmbeddingProvider(api_key="sk-fake-key-for-init-test")
        assert p.provider_name == "openai"

    def test_default_provider_from_env_is_mock(self):
        """conftest sets EMBEDDING_PROVIDER=mock."""
        from app.embeddings.factory import get_default_embedding_provider
        from app.embeddings.providers import MockEmbeddingProvider
        provider = get_default_embedding_provider()
        assert isinstance(provider, MockEmbeddingProvider)


# ─────────────────────────────────────────────────────────────────────────────
# EmbeddingService Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbeddingService:
    """Tests for the EmbeddingService wrapper class."""

    def _make_request(self, texts: list[str] | None = None):
        from app.embeddings.schemas import EmbeddingRequest
        return EmbeddingRequest(texts=texts or ["Generate an embedding for this."])

    def test_service_with_mock_provider_embeds_text(self):
        from app.embeddings.providers import MockEmbeddingProvider
        from app.services.embedding_service import EmbeddingService
        service = EmbeddingService(provider=MockEmbeddingProvider(dims=8))
        resp = service.embed_texts(self._make_request())
        assert resp.provider == "mock"
        assert len(resp.items) == 1

    def test_service_get_provider_info(self):
        from app.embeddings.providers import MockEmbeddingProvider
        from app.services.embedding_service import EmbeddingService
        service = EmbeddingService(provider=MockEmbeddingProvider(dims=8))
        info = service.get_provider_info()
        assert info.provider == "mock"
        assert info.configured is True
        assert info.dimensions == 8

    def test_service_response_has_correct_dimensions(self):
        from app.embeddings.providers import MockEmbeddingProvider
        from app.services.embedding_service import EmbeddingService
        service = EmbeddingService(provider=MockEmbeddingProvider(dims=16))
        resp = service.embed_texts(self._make_request())
        assert resp.dimensions == 16
        assert len(resp.items[0].embedding) == 16

    def test_service_embed_multiple_texts(self):
        from app.embeddings.providers import MockEmbeddingProvider
        from app.services.embedding_service import EmbeddingService
        from app.embeddings.schemas import EmbeddingRequest
        service = EmbeddingService(provider=MockEmbeddingProvider(dims=8))
        req = EmbeddingRequest(texts=["Alpha.", "Beta.", "Gamma."])
        resp = service.embed_texts(req)
        assert len(resp.items) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Exception Hierarchy Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmbeddingExceptions:
    """Tests for the embedding exception hierarchy."""

    def test_configuration_error_is_embedding_error(self):
        from app.embeddings.exceptions import EmbeddingError, EmbeddingConfigurationError
        exc = EmbeddingConfigurationError("missing key", provider="gemini")
        assert isinstance(exc, EmbeddingError)
        assert exc.provider == "gemini"

    def test_provider_error_is_embedding_error(self):
        from app.embeddings.exceptions import EmbeddingError, EmbeddingProviderError
        exc = EmbeddingProviderError("call failed", provider="openai", details={"code": 429})
        assert isinstance(exc, EmbeddingError)
        assert exc.details == {"code": 429}

    def test_message_preserved(self):
        from app.embeddings.exceptions import EmbeddingConfigurationError
        exc = EmbeddingConfigurationError("API key missing")
        assert exc.message == "API key missing"
        assert str(exc) == "API key missing"


# ─────────────────────────────────────────────────────────────────────────────
# BaseEmbeddingProvider helper tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBaseEmbeddingProviderHelpers:
    """Test shared helpers on the base class via MockEmbeddingProvider."""

    def test_estimate_token_count_returns_positive_int(self):
        from app.embeddings.providers import MockEmbeddingProvider
        p = MockEmbeddingProvider(dims=8)
        count = p._estimate_token_count("This is a sample sentence.")
        assert isinstance(count, int)
        assert count > 0

    def test_estimate_token_count_longer_text_is_larger(self):
        from app.embeddings.providers import MockEmbeddingProvider
        p = MockEmbeddingProvider(dims=8)
        short = p._estimate_token_count("Hi.")
        long = p._estimate_token_count(
            "This is a much longer sentence with many more words in it."
        )
        assert long > short

    def test_repr_includes_provider_name(self):
        from app.embeddings.providers import MockEmbeddingProvider
        p = MockEmbeddingProvider(dims=8)
        assert "mock" in repr(p).lower()
