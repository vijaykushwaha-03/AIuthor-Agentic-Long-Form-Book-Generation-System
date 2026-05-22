from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject
    from app.models.memory import FactRegistry


class Chapter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores each chapter and all intermediate text versions."""

    __tablename__ = "chapters"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chapter_contract: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    draft_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    humanized_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="planned", index=True
    )
    word_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="chapters")
    facts: Mapped[list[FactRegistry]] = relationship(
        "FactRegistry",
        back_populates="chapter",
    )

    __table_args__ = (
        UniqueConstraint("book_id", "chapter_number", name="uq_chapters_book_id_chapter_number"),
    )
