"""
AIuthor Backend — pgvector Readiness Utilities.

Provides helper functions to check whether the pgvector extension is
installed in the connected PostgreSQL database.

IMPORTANT:
  - This module does NOT create the extension automatically.
  - Extension creation will happen via an Alembic migration in Module 6.0B.
  - These functions are safe to call against SQLite test databases
    (they will gracefully return False / unavailable status).
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def is_pgvector_available(db: Session) -> bool:
    """
    Check whether the pgvector (vector) extension is installed.

    Returns False for non-PostgreSQL (like SQLite). For PostgreSQL, checks the
    pg_extension catalog and does NOT silently swallow errors.

    Args:
        db: An active SQLAlchemy Session.

    Returns:
        True  — pgvector extension is present in the connected database.
        False — running on non-PostgreSQL database.
    """
    try:
        is_pg = db.bind.dialect.name == "postgresql"
    except Exception:
        is_pg = False

    if not is_pg:
        return False

    # For PostgreSQL, execute query. Do not swallow exceptions so that connection/permission errors bubble up.
    result = db.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ")"
        )
    )
    row = result.fetchone()
    return bool(row[0]) if row else False


def assert_pgvector_ready(db: Session) -> None:
    """
    Assert that the pgvector extension is installed and ready if running on PostgreSQL.
    Raises ServiceError if running on PostgreSQL and the extension is missing.
    No-op on SQLite.
    """
    try:
        is_pg = db.bind.dialect.name == "postgresql"
    except Exception:
        is_pg = False

    if is_pg:
        if not is_pgvector_available(db):
            from app.services.exceptions import ServiceError
            raise ServiceError(
                message="pgvector extension 'vector' is not enabled on this PostgreSQL database. "
                        "Please run 'CREATE EXTENSION IF NOT EXISTS vector;' as superuser.",
                code="pgvector_missing"
            )


def get_pgvector_status(db: Session) -> dict:
    """
    Return a structured status dict for the pgvector extension.

    Args:
        db: An active SQLAlchemy Session.

    Returns:
        dict with keys:
            available (bool)   — whether pgvector is installed.
            extension_name (str) — always "vector".
            message (str)      — human-readable summary.
    """
    try:
        available = is_pgvector_available(db)
    except Exception as exc:
        available = False
        logger.error("Error during pgvector status check: %s", exc)

    if available:
        message = "pgvector extension is installed and available."
    else:
        message = (
            "pgvector extension is not installed. "
            "Run 'CREATE EXTENSION IF NOT EXISTS vector;' in PostgreSQL, "
            "or run the Module 6.0B migration."
        )

    return {
        "available": available,
        "extension_name": "vector",
        "message": message,
    }
