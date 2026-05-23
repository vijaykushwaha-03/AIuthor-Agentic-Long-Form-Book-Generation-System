"""
AIuthor Backend — DB Utilities Package.

Provides database-level helpers that sit above the ORM model layer
but below the service layer.
"""
from __future__ import annotations

from app.db.pgvector_check import is_pgvector_available, get_pgvector_status

__all__ = [
    "is_pgvector_available",
    "get_pgvector_status",
]
