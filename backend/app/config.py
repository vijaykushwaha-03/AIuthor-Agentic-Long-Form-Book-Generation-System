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
