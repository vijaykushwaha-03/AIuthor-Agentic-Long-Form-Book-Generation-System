"""
AIuthor Backend — Centralised Configuration.

Loaded once via get_settings() (cached with @lru_cache).
All values come from environment variables or a .env file.
See .env.example for the full list and defaults.

Decision DEC-002: pydantic-settings for type-safe, validated config.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        # Look for .env in the backend/ directory (one level up from app/)
        env_file=".env",
        env_file_encoding="utf-8",
        # Allow extra fields so future modules can add vars without breaking here
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: str = Field(default="development", description="Runtime environment")
    APP_VERSION: str = Field(default="0.1.0", description="Semantic version")
    SECRET_KEY: str = Field(
        default="insecure-dev-secret-change-me",
        description="Used for signing tokens. MUST be changed in production.",
    )
    LOG_LEVEL: str = Field(default="INFO", description="Python logging level")

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://aiuthor:aiuthor_secret@localhost:5432/aiuthor_db",
        description="SQLAlchemy-format DB connection URL",
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # ── LLM Provider ─────────────────────────────────────────────────────────
    LLM_PROVIDER: str = Field(
        default="gemini",
        description="Active LLM provider: 'gemini', 'openai', or 'mock'.",
    )

    # Gemini
    GEMINI_API_KEY: str = Field(default="", description="Google AI / Gemini API key.")
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model name (e.g. gemini-2.5-flash, gemini-1.5-pro).",
    )

    # OpenAI
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key.")
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model name (e.g. gpt-4o-mini, gpt-4o).",
    )

    # Shared tunables
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature applied to all providers.",
    )
    LLM_MAX_OUTPUT_TOKENS: int = Field(
        default=4000,
        gt=0,
        description="Maximum output tokens in the model response.",
    )
    LLM_TIMEOUT_SECONDS: int = Field(
        default=60,
        gt=0,
        description="HTTP timeout in seconds for LLM API calls.",
    )

    # ── Computed helpers ──────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> List[str]:
        """Return ALLOWED_ORIGINS as a Python list (split on comma)."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}, got '{v}'")
        return upper

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid = {"development", "staging", "production", "test"}
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"APP_ENV must be one of {valid}, got '{v}'")
        return lower

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        valid = {"gemini", "openai", "mock"}
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"LLM_PROVIDER must be one of {valid}, got '{v}'")
        return lower

    # ── Embedding Provider ────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = Field(
        default="gemini",
        description="Active embedding provider: 'gemini', 'openai', or 'mock'.",
    )

    # Gemini Embeddings
    GEMINI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-004",
        description="Gemini embedding model name.",
    )

    # OpenAI Embeddings
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model name.",
    )
    OPENAI_EMBEDDING_DIMENSIONS: int = Field(
        default=1536,
        gt=0,
        description="Output dimensions for OpenAI embedding model.",
    )

    # Shared embedding tunables
    EMBEDDING_DIMENSIONS: int = Field(
        default=768,
        gt=0,
        description="Default embedding vector dimensions (Gemini-oriented default).",
    )
    EMBEDDING_BATCH_SIZE: int = Field(
        default=32,
        ge=1,
        le=256,
        description="Number of texts per embedding API batch.",
    )

    @field_validator("EMBEDDING_PROVIDER")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        valid = {"gemini", "openai", "mock"}
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"EMBEDDING_PROVIDER must be one of {valid}, got '{v}'")
        return lower

    RAG_VECTOR_DIMENSIONS: int = Field(
        default=768,
        gt=0,
        description=(
            "Dimensions for stored RAG chunk embedding vectors. "
            "ALL chunk embeddings MUST have exactly this many dimensions. "
            "Default 768 matches Gemini text-embedding-004. "
            "OpenAI embeddings must request this dimension explicitly."
        ),
    )
    ALLOW_PGVECTOR_FALLBACK: bool = Field(
        default=False,
        description="Whether to fall back to Python cosine ranking on PostgreSQL if pgvector is missing.",
    )
    enable_real_agent_test_api: bool = Field(
        default=False,
        description="Whether to enable the dev-only real agent execution endpoint.",
    )
    enable_real_workflow_test_api: bool = Field(
        default=False,
        description="Whether to enable the dev-only real LangGraph workflow execution endpoint.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.

    Uses @lru_cache so environment is read only once per process.
    In tests, call get_settings.cache_clear() before overriding env vars.
    """
    settings = Settings()
    logging.basicConfig(level=settings.LOG_LEVEL)
    return settings
