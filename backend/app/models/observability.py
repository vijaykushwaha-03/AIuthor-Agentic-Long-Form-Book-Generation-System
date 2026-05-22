from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject
    from app.models.run import BookRun


class AgentTrace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores one execution trace record per agent call."""

    __tablename__ = "agent_traces"

    run_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trace_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    run: Mapped[BookRun] = relationship("BookRun", back_populates="traces")
    book: Mapped[Optional[BookProject]] = relationship("BookProject", back_populates="agent_traces")


class PromptLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores the full prompt used for every agent/LLM call."""

    __tablename__ = "prompt_logs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    prompt_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    run: Mapped[BookRun] = relationship("BookRun", back_populates="prompt_logs")
    book: Mapped[Optional[BookProject]] = relationship("BookProject", back_populates="prompt_logs")


class MemoryIOLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Logs every memory read and write."""

    __tablename__ = "memory_io_logs"

    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    run: Mapped[Optional[BookRun]] = relationship("BookRun", back_populates="memory_io_logs")
    book: Mapped[Optional[BookProject]] = relationship("BookProject", back_populates="memory_io_logs")


class TokenCostLedger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks token usage and estimated LLM cost per agent/model call."""

    __tablename__ = "token_cost_ledger"

    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    ledger_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    run: Mapped[Optional[BookRun]] = relationship("BookRun", back_populates="token_cost_entries")
    book: Mapped[Optional[BookProject]] = relationship("BookProject", back_populates="token_cost_entries")
