"""
AIuthor Backend Tests — Delivery and Reports API Layer (Module 11.0).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BookProject, Chapter
from app.config import get_settings

@pytest.fixture
def api_eval_book(db: Session) -> BookProject:
    book = BookProject(
        topic="Async Workflows in Python",
        genre="Technical",
        reader_profile="Intermediate Developers",
        tone="instructive",
        target_chapters=1,
        project_metadata={"title": "Async Python Book", "author": "Vijay Patel"},
        status="created"
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    ch = Chapter(
        book_id=book.id,
        chapter_number=1,
        title="Asyncio Event Loop",
        final_text="An event loop runs asynchronous tasks and callbacks.",
        status="completed"
    )
    db.add(ch)
    db.commit()
    return book

def test_api_evaluation_returns_report(client: TestClient, api_eval_book: BookProject):
    """1. POST /api/books/{book_id}/reports/evaluation returns report."""
    req_body = {
        "book_id": str(api_eval_book.id),
        "include_chapter_checks": True,
        "include_export_checks": True,
        "include_trace_checks": True,
        "include_memory_checks": True,
        "persist_eval_results": False
    }
    resp = client.post(f"/api/books/{api_eval_book.id}/reports/evaluation", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["book_id"] == str(api_eval_book.id)
    assert data["status"] in ("pass", "warning", "fail")
    assert "checks" in data
    assert "markdown_report" in data

def test_api_evaluation_invalid_book_returns_404(client: TestClient):
    """2. evaluation invalid book returns 404."""
    invalid_id = str(uuid4())
    req_body = {
        "book_id": invalid_id,
        "include_chapter_checks": True,
        "persist_eval_results": False
    }
    resp = client.post(f"/api/books/{invalid_id}/reports/evaluation", json=req_body)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "book_not_found"

def test_api_prompt_dossier_returns_dossier(client: TestClient):
    """3. POST /api/reports/prompt-dossier returns dossier."""
    req_body = {
        "include_templates": True,
        "include_versions": True,
        "include_agent_roles": True,
        "include_render_examples": True
    }
    resp = client.post("/api/reports/prompt-dossier", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["agent_count"] == 8
    assert "markdown_dossier" in data
    assert len(data["prompts"]) == 8

def test_api_delivery_bundle_generation(client: TestClient, api_eval_book: BookProject, tmp_path):
    """4. POST /api/books/{book_id}/delivery-bundle returns artifacts."""
    settings = get_settings()
    settings.delivery_output_dir = str(tmp_path)

    req_body = {
        "book_id": str(api_eval_book.id),
        "include_eval_report": True,
        "include_prompt_dossier": True,
        "include_architecture_summary": True,
        "include_memory_report": True,
        "include_trace_summary": True,
        "include_export_summary": True,
        "write_files": True
    }
    resp = client.post(f"/api/books/{api_eval_book.id}/delivery-bundle", json=req_body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["artifacts"]) == 7

def test_api_latest_bundle_manifest(client: TestClient, api_eval_book: BookProject, tmp_path):
    """5 & 6. latest bundle returns manifest after creation, 404 if missing."""
    settings = get_settings()
    settings.delivery_output_dir = str(tmp_path)

    # 1. Check missing returns 404
    resp = client.get(f"/api/books/{api_eval_book.id}/delivery-bundle/latest")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "bundle_not_found"

    # 2. Generate bundle
    req_body = {
        "book_id": str(api_eval_book.id),
        "write_files": True
    }
    client.post(f"/api/books/{api_eval_book.id}/delivery-bundle", json=req_body)

    # 3. Check again returns 200
    resp2 = client.get(f"/api/books/{api_eval_book.id}/delivery-bundle/latest")
    assert resp2.status_code == 200, resp2.text
    data = resp2.json()
    assert data["book_id"] == str(api_eval_book.id)
    assert data["status"] == "success"
    assert len(data["artifacts"]) == 6 # written list has 6 elements in manifest.json

def test_openapi_includes_delivery_report_endpoints(client: TestClient):
    """7. OpenAPI includes delivery report endpoints."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/books/{book_id}/reports/evaluation" in paths
    assert "/api/reports/prompt-dossier" in paths
    assert "/api/books/{book_id}/delivery-bundle" in paths
    assert "/api/books/{book_id}/delivery-bundle/latest" in paths

def test_api_calls_do_not_call_llm(client: TestClient, api_eval_book: BookProject):
    """8. API calls do not call Gemini/OpenAI."""
    # Verifies standard endpoints don't fail due to lack of API keys, indicating no LLM calls
    req_body = {
        "book_id": str(api_eval_book.id),
        "include_chapter_checks": True,
        "persist_eval_results": False
    }
    resp = client.post(f"/api/books/{api_eval_book.id}/reports/evaluation", json=req_body)
    assert resp.status_code == 200
