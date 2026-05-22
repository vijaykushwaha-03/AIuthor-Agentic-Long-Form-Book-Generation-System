from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject
    from app.models.run import BookRun


class EvalResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores automated evaluation results for generated books and generation runs."""

    __tablename__ = "eval_results"

    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    eval_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    run: Mapped[Optional[BookRun]] = relationship("BookRun", back_populates="eval_results")
    book: Mapped[BookProject] = relationship("BookProject", back_populates="eval_results")

    __table_args__ = (
        Index("idx_eval_results_created_at", "created_at"),
    )
