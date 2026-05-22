from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject


class SourceDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores raw or extracted source material used later by the Researcher agent and RAG pipeline."""

    __tablename__ = "source_documents"

    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="created", index=True
    )

    # Relationships
    book: Mapped[Optional[BookProject]] = relationship(
        "BookProject", back_populates="source_documents"
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_source_documents_created_at", "created_at"),
    )


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores text chunks generated from source documents."""

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    # Relationships
    document: Mapped[SourceDocument] = relationship("SourceDocument", back_populates="chunks")
    book: Mapped[Optional[BookProject]] = relationship(
        "BookProject", back_populates="document_chunks"
    )

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_id_chunk_index"),
        Index("idx_document_chunks_created_at", "created_at"),
    )
