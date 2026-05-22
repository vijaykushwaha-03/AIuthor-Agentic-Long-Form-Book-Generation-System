from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.book import BookProject
    from app.models.run import BookRun


class ExportFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stores generated output file records."""

    __tablename__ = "export_files"

    book_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("book_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("book_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    export_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created", index=True)
    export_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    book: Mapped[BookProject] = relationship("BookProject", back_populates="export_files")
    run: Mapped[Optional[BookRun]] = relationship("BookRun", back_populates="export_files")

    __table_args__ = (
        Index("idx_export_files_created_at", "created_at"),
    )
