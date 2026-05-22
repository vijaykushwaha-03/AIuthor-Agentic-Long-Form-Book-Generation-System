"""
AIuthor Backend Tests — Pytest Fixtures.

Decision DEC-004: Override DB dependency with in-memory SQLite so
tests run without a running Postgres instance.

Decision DEC-003: Tests call create_app() directly for isolation.

IMPORTANT: Environment variables MUST be set before any app module
is imported, because pydantic-settings reads env at class load time
and lru_cache persists the Settings object across calls.
"""
from __future__ import annotations

import os

# ── Set test environment FIRST — before any app imports ───────────────────────
os.environ["APP_ENV"] = "test"
os.environ["APP_VERSION"] = "0.1.0"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ── In-memory SQLite engine for tests ────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite in-memory
    poolclass=StaticPool,                       # Single connection for in-memory
)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=_test_engine,
)


def override_get_db():
    """SQLite session override — replaces Postgres session in tests."""
    db = TestSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def app():
    """
    Create a test FastAPI app instance.

    - Clears Settings lru_cache so test env vars are picked up.
    - Resets the lazy DB engine globals so SQLite URL is used.
    - Overrides the get_db dependency with the SQLite override.
    """
    # Clear cached settings so test env vars are read fresh
    from app.config import get_settings
    get_settings.cache_clear()

    # Reset lazy engine globals so engine is rebuilt with SQLite URL
    import app.database as db_module
    db_module._engine = None
    db_module._session_local = None

    from app.database import get_db
    from app.main import create_app

    test_app = create_app()
    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.fixture(scope="session")
def client(app):
    """
    Return an httpx TestClient wrapping the test app.
    Session-scoped: one client instance for the entire test run.
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
