"""
AIuthor Backend — Database Engine and Session Dependency.

Module 1 sets up the synchronous SQLAlchemy engine and a
get_db() FastAPI dependency. Models and Alembic migrations
are added in Module 2.

Decision DEC-001: sync SQLAlchemy for Module 1 simplicity.
Decision DEC-004: tests override this dependency with SQLite.
"""
from __future__ import annotations

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Declarative base for ORM models ──────────────────────────────────────────
class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this base."""
    pass


# ── Lazy engine factory ───────────────────────────────────────────────────────
# We do NOT create the engine at module import time.
# Instead it is created on first call to get_engine().
# This lets tests set environment variables (and clear lru_cache)
# before the engine is built.
_engine = None
_session_local = None


def get_engine():
    """Return the singleton SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.DATABASE_URL

        # SQLite (used in tests) does not support pool_size / max_overflow
        is_sqlite = url.startswith("sqlite")

        engine_kwargs: dict = {
            "pool_pre_ping": not is_sqlite,  # SQLite does not need ping
            "echo": (settings.APP_ENV == "development"),
        }

        if not is_sqlite:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10

        _engine = create_engine(url, **engine_kwargs)
        logger.debug("SQLAlchemy engine created for: %s", url.split("@")[-1])

    return _engine


def get_session_local():
    """Return the sessionmaker factory, creating it on first call."""
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
        )
    return _session_local


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that yields a database session per request.
    The session is closed (and transaction rolled back on error) after
    the request completes.

    Usage in a route:
        @router.get("/")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ping_db() -> bool:
    """
    Execute a lightweight query to verify the database is reachable.
    Called during the FastAPI startup lifespan event.

    Returns True on success, raises on failure.
    """
    SessionLocal = get_session_local()
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    logger.info("Database ping successful.")
    return True
