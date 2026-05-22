from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.book import BookProject
from app.models.run import BookRun
from app.models.eval import EvalResult
from app.models.export import ExportFile


def test_base_metadata_contains_eval_export_tables():
    """Verify that all eval and export tables are registered in SQLAlchemy metadata."""
    expected_tables = {
        "eval_results",
        "export_files",
    }
    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_eval_export_models_lifecycle():
    """Verify instantiation, relationships, defaults, cascades, and constraints on SQLite."""
    # Setup in-memory SQLite database for isolated unit test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. Instantiate BookProject
        project = BookProject(
            topic="Test Finance Guide",
            reader_profile="Young adults",
            genre="Finance",
            tone="Conversational",
            target_chapters=5,
            words_per_chapter=1000,
            status="created",
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # 2. Instantiate BookRun
        run = BookRun(
            book_id=project.id,
            status="pending",
            current_agent="PlannerAgent",
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        # 3. Instantiate EvalResult
        eval_res = EvalResult(
            run_id=run.id,
            book_id=project.id,
            eval_name="structure_eval",
            score=0.95,
            status="passed",
            details={"chapter_count": 5, "checks": ["toc_valid", "chapters_match"]},
        )
        session.add(eval_res)
        session.commit()
        session.refresh(eval_res)

        assert isinstance(eval_res.id, uuid.UUID)
        assert eval_res.run_id == run.id
        assert eval_res.book_id == project.id
        assert eval_res.eval_name == "structure_eval"
        assert eval_res.score == 0.95
        assert eval_res.status == "passed"
        assert eval_res.details == {"chapter_count": 5, "checks": ["toc_valid", "chapters_match"]}
        assert eval_res.run == run
        assert eval_res.book == project
        assert eval_res in run.eval_results
        assert eval_res in project.eval_results
        assert isinstance(eval_res.created_at, datetime)
        assert isinstance(eval_res.updated_at, datetime)

        # 4. Instantiate ExportFile (verifying status defaults to "created")
        export_file = ExportFile(
            book_id=project.id,
            run_id=run.id,
            export_type="pdf",
            file_path="/exports/book_final.pdf",
            file_name="book_final.pdf",
            mime_type="application/pdf",
            export_metadata={"pages": 120},
        )
        session.add(export_file)
        session.commit()
        session.refresh(export_file)

        assert isinstance(export_file.id, uuid.UUID)
        assert export_file.book_id == project.id
        assert export_file.run_id == run.id
        assert export_file.export_type == "pdf"
        assert export_file.file_path == "/exports/book_final.pdf"
        assert export_file.file_name == "book_final.pdf"
        assert export_file.mime_type == "application/pdf"
        assert export_file.status == "created"  # Verified default
        assert export_file.export_metadata == {"pages": 120}
        assert export_file.book == project
        assert export_file.run == run
        assert export_file in project.export_files
        assert export_file in run.export_files
        assert isinstance(export_file.created_at, datetime)
        assert isinstance(export_file.updated_at, datetime)

        # 5. Check run-level cascade delete behavior
        session.delete(run)
        session.commit()

        # Run deleted: run_id is foreign key ondelete='CASCADE' in both tables
        assert session.query(EvalResult).filter_by(run_id=run.id).count() == 0
        assert session.query(ExportFile).filter_by(run_id=run.id).count() == 0
