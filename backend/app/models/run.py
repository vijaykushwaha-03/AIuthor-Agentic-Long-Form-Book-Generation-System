from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject
    from app.models.observability import (
        AgentTrace,
        PromptLog,
        MemoryIOLog,
        TokenCostLedger,
    )
    from app.models.eval import EvalResult
    from app.models.export import ExportFile


class BookRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores one execution of the generation workflow."""

    __tablename__ = "book_runs"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )
    current_agent: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="runs")
    traces: Mapped[list[AgentTrace]] = relationship(
        "AgentTrace",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    prompt_logs: Mapped[list[PromptLog]] = relationship(
        "PromptLog",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    memory_io_logs: Mapped[list[MemoryIOLog]] = relationship(
        "MemoryIOLog",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    token_cost_entries: Mapped[list[TokenCostLedger]] = relationship(
        "TokenCostLedger",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    eval_results: Mapped[list[EvalResult]] = relationship(
        "EvalResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    export_files: Mapped[list[ExportFile]] = relationship(
        "ExportFile",
        back_populates="run",
        cascade="all, delete-orphan",
    )
