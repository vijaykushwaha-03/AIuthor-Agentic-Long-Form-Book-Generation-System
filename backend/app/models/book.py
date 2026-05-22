from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.run import BookRun
    from app.models.chapter import Chapter
    from app.models.document import SourceDocument, DocumentChunk
    from app.models.memory import (
        FactRegistry,
        ConceptBible,
        CharacterBible,
        CallbackIndex,
        ToneFingerprint,
        DecisionLog,
    )
    from app.models.observability import (
        AgentTrace,
        PromptLog,
        MemoryIOLog,
        TokenCostLedger,
    )
    from app.models.eval import EvalResult
    from app.models.export import ExportFile


class BookProject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores one book project created from the user brief."""

    __tablename__ = "book_projects"

    topic: Mapped[str] = mapped_column(Text, nullable=False)
    reader_profile: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_chapters: Mapped[int] = mapped_column(Integer, nullable=False)
    words_per_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="created", index=True
    )
    project_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    runs: Mapped[list[BookRun]] = relationship(
        "BookRun",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    chapters: Mapped[list[Chapter]] = relationship(
        "Chapter",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Chapter.chapter_number",
    )
    sections: Mapped[list[BookSection]] = relationship(
        "BookSection",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="BookSection.sort_order",
    )
    source_documents: Mapped[list[SourceDocument]] = relationship(
        "SourceDocument",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    document_chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    facts: Mapped[list[FactRegistry]] = relationship(
        "FactRegistry",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    concepts: Mapped[list[ConceptBible]] = relationship(
        "ConceptBible",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    characters: Mapped[list[CharacterBible]] = relationship(
        "CharacterBible",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    callbacks: Mapped[list[CallbackIndex]] = relationship(
        "CallbackIndex",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    tone_fingerprints: Mapped[list[ToneFingerprint]] = relationship(
        "ToneFingerprint",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    decision_logs: Mapped[list[DecisionLog]] = relationship(
        "DecisionLog",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    agent_traces: Mapped[list[AgentTrace]] = relationship(
        "AgentTrace",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    prompt_logs: Mapped[list[PromptLog]] = relationship(
        "PromptLog",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    memory_io_logs: Mapped[list[MemoryIOLog]] = relationship(
        "MemoryIOLog",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    token_cost_entries: Mapped[list[TokenCostLedger]] = relationship(
        "TokenCostLedger",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    eval_results: Mapped[list[EvalResult]] = relationship(
        "EvalResult",
        back_populates="book",
        cascade="all, delete-orphan",
    )
    export_files: Mapped[list[ExportFile]] = relationship(
        "ExportFile",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_book_projects_created_at", "created_at"),
    )


class BookSection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores all front matter and back matter sections."""

    __tablename__ = "book_sections"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft", index=True
    )
    section_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="sections")
