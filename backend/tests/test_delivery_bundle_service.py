"""
AIuthor Backend Tests — Delivery Bundle Service (Module 11.0).
"""
from __future__ import annotations

import os
import json
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter
from app.config import get_settings
from app.services.delivery_bundle_service import DeliveryBundleService
from app.workflows.schemas import DeliveryBundleRequest

@pytest.fixture
def bundle_book(db: Session) -> BookProject:
    book = BookProject(
        topic="Symmetric Encryption",
        genre="Technical",
        reader_profile="Security Students",
        tone="didactic",
        target_chapters=1,
        project_metadata={"title": "Crypto 101", "subtitle": "Symmetric Ciphers", "author": "Vijay Patel"},
        status="created"
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    ch = Chapter(
        book_id=book.id,
        chapter_number=1,
        title="AES cipher",
        final_text="Advanced Encryption Standard details and specifications.",
        status="completed"
    )
    db.add(ch)
    db.commit()
    return book

def test_generate_delivery_bundle_returns_manifest(db: Session, bundle_book: BookProject, tmp_path):
    """1. generate_delivery_bundle returns manifest structure."""
    settings = get_settings()
    settings.delivery_output_dir = str(tmp_path)

    svc = DeliveryBundleService(db)
    req = DeliveryBundleRequest(
        book_id=bundle_book.id,
        include_eval_report=True,
        include_prompt_dossier=True,
        include_architecture_summary=True,
        include_memory_report=True,
        include_trace_summary=True,
        include_export_summary=True,
        write_files=False
    )
    res = svc.generate_delivery_bundle(req)
    assert res.status == "success"
    assert res.book_id == bundle_book.id
    assert res.manifest["book_id"] == str(bundle_book.id)
    assert len(res.artifacts) == 6
    for art in res.artifacts:
        assert art.status == "skipped_write"

def test_write_files_true_writes_all_files(db: Session, bundle_book: BookProject, tmp_path):
    """2 to 9. write_files=true writes files to disk."""
    settings = get_settings()
    settings.delivery_output_dir = str(tmp_path)

    svc = DeliveryBundleService(db)
    req = DeliveryBundleRequest(
        book_id=bundle_book.id,
        include_eval_report=True,
        include_prompt_dossier=True,
        include_architecture_summary=True,
        include_memory_report=True,
        include_trace_summary=True,
        include_export_summary=True,
        write_files=True
    )
    res = svc.generate_delivery_bundle(req)
    assert res.status == "success"
    assert len(res.artifacts) == 7 # 6 + manifest.json

    dest_dir = tmp_path / str(bundle_book.id) / "manual"
    assert dest_dir.exists()

    expected_files = [
        "evaluation_report.md",
        "prompt_dossier.md",
        "architecture_summary.md",
        "memory_report.md",
        "trace_summary.md",
        "export_summary.md",
        "manifest.json",
    ]
    for filename in expected_files:
        p = dest_dir / filename
        assert p.exists()
        assert p.stat().st_size > 0

    # Verify manifest JSON can be parsed
    with open(dest_dir / "manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["book_id"] == str(bundle_book.id)
        assert data["status"] == "success"
        assert len(data["artifacts"]) == 6 # manifest itself isn't listed in the serialized list inside the written file typically, or is listed. Let's make sure it's correct.

def test_write_files_false_writes_no_files(db: Session, bundle_book: BookProject, tmp_path):
    """10. write_files=false writes no files but returns manifest."""
    settings = get_settings()
    settings.delivery_output_dir = str(tmp_path)

    svc = DeliveryBundleService(db)
    req = DeliveryBundleRequest(
        book_id=bundle_book.id,
        include_eval_report=True,
        include_prompt_dossier=True,
        include_architecture_summary=True,
        include_memory_report=True,
        include_trace_summary=True,
        include_export_summary=True,
        write_files=False
    )
    svc.generate_delivery_bundle(req)
    dest_dir = tmp_path / str(bundle_book.id) / "manual"
    assert not dest_dir.exists()
