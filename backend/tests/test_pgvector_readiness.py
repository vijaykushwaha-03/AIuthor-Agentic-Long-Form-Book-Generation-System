"""
AIuthor Backend — Tests: pgvector Readiness Utility (Module 6.0A).

Tests for is_pgvector_available() and get_pgvector_status().

IMPORTANT:
  - Tests run against the in-memory SQLite test database.
  - pgvector is NOT expected to be installed.
  - Functions must return False/unavailable gracefully against SQLite.
  - No extension is created by any test.
"""
from __future__ import annotations

import pytest


class TestPgvectorReadiness:
    """Tests for pgvector readiness utilities."""

    def test_is_pgvector_available_returns_bool(self):
        """is_pgvector_available must return a bool, not raise."""
        from app.db.pgvector_check import is_pgvector_available
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            result = is_pgvector_available(db)
            assert isinstance(result, bool)
        finally:
            db.close()

    def test_is_pgvector_available_false_on_sqlite(self):
        """SQLite does not have pg_extension; should return False without raising."""
        from app.db.pgvector_check import is_pgvector_available
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            result = is_pgvector_available(db)
            assert result is False
        finally:
            db.close()

    def test_get_pgvector_status_returns_dict(self):
        """get_pgvector_status must return a dict with the expected keys."""
        from app.db.pgvector_check import get_pgvector_status
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            status = get_pgvector_status(db)
            assert isinstance(status, dict)
        finally:
            db.close()

    def test_get_pgvector_status_has_required_keys(self):
        """Result dict must have 'available', 'extension_name', 'message'."""
        from app.db.pgvector_check import get_pgvector_status
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            status = get_pgvector_status(db)
            assert "available" in status
            assert "extension_name" in status
            assert "message" in status
        finally:
            db.close()

    def test_get_pgvector_status_extension_name_is_vector(self):
        from app.db.pgvector_check import get_pgvector_status
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            status = get_pgvector_status(db)
            assert status["extension_name"] == "vector"
        finally:
            db.close()

    def test_get_pgvector_status_available_false_on_sqlite(self):
        """SQLite test DB does not have pgvector; available must be False."""
        from app.db.pgvector_check import get_pgvector_status
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            status = get_pgvector_status(db)
            assert status["available"] is False
        finally:
            db.close()

    def test_get_pgvector_status_message_is_string(self):
        from app.db.pgvector_check import get_pgvector_status
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            status = get_pgvector_status(db)
            assert isinstance(status["message"], str)
            assert len(status["message"]) > 0
        finally:
            db.close()

    def test_does_not_create_extension(self):
        """Running pgvector check should not create any extension in the DB."""
        from app.db.pgvector_check import get_pgvector_status
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db = sessionmaker(bind=engine)()
        try:
            get_pgvector_status(db)
            # Run check again — should still return False, not True
            result2 = get_pgvector_status(db)
            assert result2["available"] is False
        finally:
            db.close()
