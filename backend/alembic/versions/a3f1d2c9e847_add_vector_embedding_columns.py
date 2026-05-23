"""add vector embedding columns to document_chunks

Revision ID: a3f1d2c9e847
Revises: 0d3dd892d8be
Create Date: 2026-05-23 13:15:00.000000

PURPOSE:
  - Enable pgvector extension (PostgreSQL only).
  - Add 5 vector-storage columns to document_chunks:
      embedding           VECTOR(768) / nullable
      embedding_provider  VARCHAR(100) / nullable
      embedding_dimensions INTEGER / nullable
      embedding_created_at TIMESTAMP / nullable
      embedding_error     TEXT / nullable

IMPORTANT:
  - This migration is designed for PostgreSQL with the pgvector extension.
  - On SQLite (used in tests) the vector-specific DDL is skipped safely.
  - If pgvector is NOT installed on your PostgreSQL server, run:
        psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
    before running this migration.
  - Downgrade removes the five new columns but does NOT drop the
    pgvector extension (other objects may rely on it).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f1d2c9e847"
down_revision: Union[str, None] = "0d3dd892d8be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Dimension constant — must match settings.RAG_VECTOR_DIMENSIONS.
_RAG_VECTOR_DIMENSIONS = 768


def _is_postgresql() -> bool:
    """Return True when the connected dialect is PostgreSQL."""
    try:
        bind = op.get_bind()
        return bind.dialect.name == "postgresql"
    except Exception:
        return False


def upgrade() -> None:
    is_pg = _is_postgresql()
    has_vector_extension = False

    if is_pg:
        try:
            bind = op.get_bind()
            result = bind.execute(sa.text("SELECT name FROM pg_available_extensions WHERE name = 'vector'")).fetchone()
            has_vector_extension = (result is not None)
        except Exception:
            has_vector_extension = False

    if has_vector_extension:
        # Enable pgvector extension. Idempotent — safe to run multiple times.
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Add the native Vector column on PostgreSQL.
        # We use raw SQL because Alembic's add_column does not know pgvector types.
        op.execute(
            f"ALTER TABLE document_chunks "
            f"ADD COLUMN IF NOT EXISTS embedding vector({_RAG_VECTOR_DIMENSIONS})"
        )
    else:
        # SQLite / PG without pgvector: store embedding as a JSON list.
        op.add_column("document_chunks", sa.Column("embedding", sa.JSON(), nullable=True))

    # Add remaining columns — these are dialect-agnostic.
    op.add_column(
        "document_chunks",
        sa.Column("embedding_provider", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "embedding_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "embedding_error")
    op.drop_column("document_chunks", "embedding_created_at")
    op.drop_column("document_chunks", "embedding_dimensions")
    op.drop_column("document_chunks", "embedding_provider")
    op.drop_column("document_chunks", "embedding")
    # NOTE: pgvector extension is intentionally NOT dropped in downgrade.
    # Other database objects may depend on it after future migrations.
