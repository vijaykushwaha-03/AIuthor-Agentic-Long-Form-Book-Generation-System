#!/usr/bin/env python
"""AIuthor Backend — Database Inspection Script.

Verifies database connectivity and lists all created tables.
"""
from __future__ import annotations

import sys
import os

# Add parent directory to sys.path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect
from app.database import get_engine, ping_db


def main():
    try:
        # Ping DB
        ping_db()
        print("Database connection: OK")

        # Get discovered tables
        engine = get_engine()
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            "book_projects",
            "book_runs",
            "chapters",
            "book_sections",
            "source_documents",
            "document_chunks",
            "fact_registry",
            "concept_bible",
            "character_bible",
            "callback_index",
            "tone_fingerprints",
            "decision_log",
            "agent_traces",
            "prompt_logs",
            "memory_io_logs",
            "token_cost_ledger",
            "eval_results",
            "export_files",
        }

        print("Tables found in database:")
        for table in sorted(tables):
            if table in expected_tables:
                print(f"- {table}")

        missing_tables = expected_tables - tables
        if missing_tables:
            print(f"CRITICAL: Missing tables: {sorted(list(missing_tables))}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Database verification: SUCCESS. All {len(expected_tables)} expected tables exist.")
            sys.exit(0)
    except Exception as e:
        print(f"Database connection: FAILED ({e})", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
