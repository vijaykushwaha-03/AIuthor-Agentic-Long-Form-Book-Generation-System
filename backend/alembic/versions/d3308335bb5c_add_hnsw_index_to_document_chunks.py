"""add hnsw index to document_chunks

Revision ID: d3308335bb5c
Revises: a3f1d2c9e847
Create Date: 2026-05-23 17:58:51.386122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3308335bb5c'
down_revision: Union[str, None] = 'a3f1d2c9e847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            result = bind.execute(sa.text("SELECT name FROM pg_available_extensions WHERE name = 'vector'")).fetchone()
            has_vector = (result is not None)
        except Exception:
            has_vector = False

        if has_vector:
            # We use CREATE INDEX IF NOT EXISTS using HNSW
            op.execute(
                "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw "
                "ON document_chunks "
                "USING hnsw (embedding vector_cosine_ops);"
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding_hnsw;")
