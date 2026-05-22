from __future__ import annotations

import sys
import os
import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database import Base
import app.models as models

# The 18 expected tables
EXPECTED_TABLES = {
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


def test_base_metadata_contains_all_expected_tables():
    """Verify that SQLAlchemy metadata contains all 18 application tables and no duplicate names."""
    metadata_tables = list(Base.metadata.tables.keys())
    
    # 1. Assert exactly the 18 expected tables are in metadata (as a subset or matching)
    for table_name in EXPECTED_TABLES:
        assert table_name in Base.metadata.tables, f"Table '{table_name}' missing from metadata registry"
        
    # 2. Check for duplicate table names in metadata
    assert len(metadata_tables) == len(set(metadata_tables)), "Duplicate table names registered in metadata!"


def test_all_model_classes_importable():
    """Verify that all models can be imported from app.models."""
    model_classes = [
        "BookProject",
        "BookSection",
        "Chapter",
        "BookRun",
        "SourceDocument",
        "DocumentChunk",
        "FactRegistry",
        "ConceptBible",
        "CharacterBible",
        "CallbackIndex",
        "ToneFingerprint",
        "DecisionLog",
        "AgentTrace",
        "PromptLog",
        "MemoryIOLog",
        "TokenCostLedger",
        "EvalResult",
        "ExportFile",
    ]
    for model_class in model_classes:
        assert hasattr(models, model_class), f"app.models does not export model '{model_class}'"


def test_check_db_script_table_list_matches():
    """Verify check_db.py expected table list matches our EXPECTED_TABLES."""
    # We read backend/scripts/check_db.py and parse expected_tables dynamically or verify matches
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts/check_db.py"))
    assert os.path.exists(script_path), f"check_db.py script path not found: {script_path}"
    
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    for table_name in EXPECTED_TABLES:
        assert f'"{table_name}"' in content or f"'{table_name}'" in content, (
            f"Table '{table_name}' not referenced in check_db.py script"
        )


def test_no_vector_or_pgvector_extensions_and_tables():
    """Verify no vector or pgvector tables or extensions are registered or referenced yet."""
    # Check that no table containing 'vector' or 'pgvector' exists in the metadata
    for table_name in Base.metadata.tables:
        assert "vector" not in table_name, f"Forbidden table name '{table_name}' containing 'vector' found"
        assert "pgvector" not in table_name, f"Forbidden table name '{table_name}' containing 'pgvector' found"


def test_document_chunks_has_no_vector_column():
    """Verify that document_chunks does not have any embedding/vector columns yet (postponed to Module 6)."""
    table = Base.metadata.tables.get("document_chunks")
    assert table is not None, "document_chunks table not found in metadata"
    
    # Assert there is no 'embedding' or 'vector' column
    column_names = {col.name for col in table.columns}
    assert "embedding" not in column_names, "Forbidden 'embedding' column found in document_chunks table"
    assert "vector" not in column_names, "Forbidden 'vector' column found in document_chunks table"
    
    # Confirm types of all columns to make sure none are vector or custom vector types
    for col in table.columns:
        type_str = str(col.type).lower()
        assert "vector" not in type_str, f"Forbidden vector type detected on column {col.name}: {col.type}"
