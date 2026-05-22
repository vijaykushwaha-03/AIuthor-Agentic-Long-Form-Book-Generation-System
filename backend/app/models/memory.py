from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Integer, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject
    from app.models.chapter import Chapter
    from app.models.document import SourceDocument, DocumentChunk


class FactRegistry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores factual claims and grounding information used by Researcher, Writer, and Fact Checker agents."""

    __tablename__ = "fact_registry"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unverified", index=True
    )
    used_in_chapters: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    fact_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="facts")
    chapter: Mapped[Optional[Chapter]] = relationship("Chapter", back_populates="facts")
    source_document: Mapped[Optional[SourceDocument]] = relationship("SourceDocument")
    source_chunk: Mapped[Optional[DocumentChunk]] = relationship("DocumentChunk")


class ConceptBible(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores recurring concepts and glossary candidates."""

    __tablename__ = "concept_bible"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    related_terms: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    appears_in_chapters: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    concept_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="concepts")

    __table_args__ = (
        UniqueConstraint("book_id", "concept", name="uq_concept_bible_book_id_concept"),
    )


class CharacterBible(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores character continuity for novella and storyteller tone books."""

    __tablename__ = "character_bible"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    character_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    traits: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    relationships: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    arc_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appears_in_chapters: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)
    character_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="characters")

    __table_args__ = (
        UniqueConstraint("book_id", "character_name", name="uq_character_bible_book_id_character_name"),
    )


class CallbackIndex(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores cross-chapter callbacks and continuity references."""

    __tablename__ = "callback_index"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    target_chapter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    concept: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    callback_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active", index=True
    )
    callback_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="callbacks")


class ToneFingerprint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores tone rules used across chapters, front matter, glossary, afterword, and back-cover copy."""

    __tablename__ = "tone_fingerprints"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tone_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sentence_rhythm: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    lexical_rules: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    banned_phrases: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    example_phrases: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    fingerprint_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="tone_fingerprints")


class DecisionLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores important engineering decisions and generation decisions."""

    __tablename__ = "decision_log"

    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[Optional[BookProject]] = relationship("BookProject", back_populates="decision_logs")

    __table_args__ = (
        Index("idx_decision_log_created_at", "created_at"),
    )
