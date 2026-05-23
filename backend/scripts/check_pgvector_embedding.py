#!/usr/bin/env python
"""AIuthor Backend — pgvector and Database Audit Script.

Verifies database dialect, versions, pgvector extension state, and embedding table columns.
"""
from __future__ import annotations

import sys
import os

# Add parent directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.database import get_engine


def main():
    try:
        engine = get_engine()
        dialect = engine.dialect.name
        print(f"Database dialect detected: {dialect}")
        print(f"Database name: {engine.url.database}")
        
        # Get Alembic current revision if possible
        alembic_rev = "unknown"
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                if res:
                    alembic_rev = res[0]
            print(f"Current Alembic revision: {alembic_rev}")
        except Exception:
            print("Alembic version table not found or not initialized.")

        if dialect == "sqlite":
            print("\nSUCCESS: SQLite dialect detected.")
            print("SQLite JSON fallback is active for tests only.")
            sys.exit(0)

        elif dialect == "postgresql":
            print("\nAuditing PostgreSQL environment...")
            with engine.connect() as conn:
                # 1. Check PG server version
                version_info = conn.execute(text("SELECT version();")).fetchone()
                version_str = version_info[0] if version_info else "Unknown"
                print(f"- PostgreSQL version details: {version_str}")
                
                # Check if version is 18 (warning/failure case based on user expectation)
                if "PostgreSQL 18" in version_str:
                    print("ERROR: Detected PostgreSQL 18. Expected PostgreSQL 16 local setup.", file=sys.stderr)
                    sys.exit(1)
                
                # 2. Check pgvector extension presence
                ext_info = conn.execute(text(
                    "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
                )).fetchone()
                
                if ext_info:
                    print(f"- pgvector extension is installed: Name='{ext_info[0]}', Version='{ext_info[1]}'")
                else:
                    print("ERROR: pgvector extension ('vector') is NOT enabled/installed on this database.", file=sys.stderr)
                    print("HINT: Run 'CREATE EXTENSION IF NOT EXISTS vector;' as superuser.", file=sys.stderr)
                    
                    # Also check if it's available for installation
                    avail_info = conn.execute(text(
                        "SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name = 'vector';"
                    )).fetchone()
                    if avail_info:
                        print(f"  Note: Extension is available in packages. Default version: {avail_info[1]}.", file=sys.stderr)
                    else:
                        print("  Note: pgvector binaries are missing on this PostgreSQL server package.", file=sys.stderr)
                    sys.exit(1)
                
                # 3. Check document_chunks table columns
                print("- Auditing table: 'document_chunks'...")
                columns = conn.execute(text(
                    "SELECT column_name, data_type, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'document_chunks';"
                )).fetchall()
                
                col_map = {row[0]: (row[1], row[2]) for row in columns}
                
                required_metadata = [
                    "embedding_dimensions",
                    "embedding_provider",
                    "embedding_created_at",
                    "embedding_error"
                ]
                
                # Verify embedding column type
                if "embedding" not in col_map:
                    print("ERROR: Column 'embedding' is missing in 'document_chunks'.", file=sys.stderr)
                    sys.exit(1)
                
                data_type, udt_name = col_map["embedding"]
                print(f"  * 'embedding' column type: data_type='{data_type}', udt_name='{udt_name}'")
                
                if udt_name != "vector":
                    print(f"ERROR: 'embedding' column is NOT of type 'vector' (found '{udt_name}'/'{data_type}').", file=sys.stderr)
                    print("Please drop/recreate the column or rerun migrations with pgvector active.", file=sys.stderr)
                    sys.exit(1)
                
                # Verify metadata columns
                missing_cols = []
                for col in required_metadata:
                    if col not in col_map:
                        missing_cols.append(col)
                    else:
                        print(f"  * metadata column '{col}' exists.")
                        
                if missing_cols:
                    print(f"ERROR: Missing required embedding metadata columns: {missing_cols}", file=sys.stderr)
                    sys.exit(1)
                    
            print("\nSUCCESS: PostgreSQL 16 pgvector embedding storage is ready!")
            sys.exit(0)
            
        else:
            print(f"ERROR: Unsupported database dialect '{dialect}'.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
