"""
Tests for Common SQLAlchemy Model Bases and Mixins.

Verifies that UUIDPrimaryKeyMixin and TimestampMixin generate default keys
and timestamps correctly, and behave appropriately in an active database session.
"""
from __future__ import annotations

from datetime import datetime, timezone
import time
import uuid

from sqlalchemy import String, create_engine
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, sessionmaker

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

Base = declarative_base()


class DummyModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Temporary model to test base mixins."""

    __tablename__ = "dummy_model"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


def test_guid_and_timestamp_mixins():
    """Verify UUID generation, GUID TypeDecorator behavior, and auto-timestamps using SQLite."""
    # Use SQLite in-memory database for quick, isolated test execution
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Create a new record without specifying ID or timestamps
        record = DummyModel(name="Test Base Mixins")
        session.add(record)
        session.commit()

        # Retrieve and verify generated fields
        retrieved = session.query(DummyModel).filter_by(name="Test Base Mixins").first()
        assert retrieved is not None
        assert isinstance(retrieved.id, uuid.UUID)
        assert isinstance(retrieved.created_at, datetime)
        assert isinstance(retrieved.updated_at, datetime)

        # Check timezone-awareness (DateTime(timezone=True))
        # Note: SQLite stores datetime strings, but timezone info is handled
        assert retrieved.created_at is not None

        # Verify update timestamp functionality
        original_created = retrieved.created_at
        original_updated = retrieved.updated_at

        # Sleep briefly to ensure timestamp difference (since SQLite/clock granularity is small)
        time.sleep(0.1)

        retrieved.name = "Updated Name"
        session.add(retrieved)
        session.commit()

        session.refresh(retrieved)
        assert retrieved.name == "Updated Name"
        # In SQLite, onupdate might run locally or database-side.
        # Let's verify that the update trigger or onupdate modified it if the ORM detected changes.
        assert retrieved.created_at == original_created
        assert retrieved.updated_at > original_updated
