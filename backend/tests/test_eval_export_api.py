"""
AIuthor Backend Tests — Eval + Export API Route Tests.

Uses the session-scoped TestClient from conftest.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


# ── Payload helpers ───────────────────────────────────────────────────────────

def _book_payload(**kw) -> dict:
    return {
        "topic": "Eval Export Test Book",
        "reader_profile": "Testers",
        "genre": "Fiction",
        "tone": "conversational",
        "target_chapters": 3,
        **kw,
    }


def _create_book(client: TestClient, topic="Eval Export API Test") -> str:
    resp = client.post("/api/books", json=_book_payload(topic=topic))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_run(client: TestClient, book_id: str) -> str:
    resp = client.post(f"/api/books/{book_id}/runs", json={"book_id": book_id, "run_metadata": {"env": "test"}})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ══════════════════════════════════════════════════════════════════════════════
# Eval Result API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEvalAPI:

    def test_eval_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Eval Lifecycle API Test")
        run_id = _create_run(client, book_id)

        # 1. POST eval creates
        payload = {
            "book_id": book_id,
            "run_id": run_id,
            "eval_name": "Grammar Quality",
            "score": 0.95,
            "status": "passed",
            "details": {"typos": 0},
        }
        resp = client.post(f"/api/books/{book_id}/evals", json=payload)
        assert resp.status_code == 201, resp.text
        eval_res = resp.json()
        assert eval_res["id"] is not None
        assert eval_res["eval_name"] == "Grammar Quality"
        assert eval_res["status"] == "passed"

        # 2. GET evals lists
        resp = client.get(f"/api/books/{book_id}/evals?eval_name=Grammar Quality")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == eval_res["id"]

        # 3. GET eval detail works
        resp = client.get(f"/api/books/{book_id}/evals/{eval_res['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["eval_name"] == "Grammar Quality"

        # 4. PATCH eval updates
        resp = client.patch(
            f"/api/books/{book_id}/evals/{eval_res['id']}",
            json={"score": 0.99, "status": "passed"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["score"] == 0.99

        # 5. GET report compiles summary
        resp = client.get(f"/api/books/{book_id}/eval-report?run_id={run_id}")
        assert resp.status_code == 200, resp.text
        report = resp.json()
        assert report["overall_score"] == 0.99
        assert report["total_evals"] == 1
        assert report["passed_evals"] == 1
        assert report["overall_status"] == "passed"

        # 6. DELETE eval deletes
        resp = client.delete(f"/api/books/{book_id}/evals/{eval_res['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["message"] is not None

        # 7. GET deleted eval returns 404
        resp = client.get(f"/api/books/{book_id}/evals/{eval_res['id']}")
        assert resp.status_code == 404

    def test_post_eval_for_missing_book_returns_404(self, client: TestClient):
        fake_book_id = str(uuid4())
        payload = {
            "book_id": fake_book_id,
            "eval_name": "Grammar",
            "status": "passed",
        }
        resp = client.post(f"/api/books/{fake_book_id}/evals", json=payload)
        assert resp.status_code == 404

    def test_post_run_eval_creates_run_eval(self, client: TestClient):
        book_id = _create_book(client, "Run Scope Test")
        run_id = _create_run(client, book_id)

        payload = {
            "book_id": book_id,
            "run_id": run_id,
            "eval_name": "Style Consistency",
            "score": 0.88,
            "status": "warning",
        }
        resp = client.post(f"/api/runs/{run_id}/evals", json=payload)
        assert resp.status_code == 201, resp.text
        assert resp.json()["run_id"] == run_id


# ══════════════════════════════════════════════════════════════════════════════
# Export File API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestExportAPI:

    def test_export_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Export Lifecycle API Test")
        run_id = _create_run(client, book_id)

        # 1. POST export file creates
        payload = {
            "book_id": book_id,
            "run_id": run_id,
            "export_type": "pdf",
            "file_path": "/pending/mybook.pdf",
            "file_name": "mybook.pdf",
            "mime_type": "application/pdf",
            "status": "created",
        }
        resp = client.post(f"/api/books/{book_id}/exports", json=payload)
        assert resp.status_code == 201, resp.text
        export_file = resp.json()
        assert export_file["id"] is not None
        assert export_file["export_type"] == "pdf"
        assert export_file["status"] == "created"

        # 2. GET exports lists
        resp = client.get(f"/api/books/{book_id}/exports?export_type=pdf")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == export_file["id"]

        # 3. GET export detail works
        resp = client.get(f"/api/books/{book_id}/exports/{export_file['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["file_name"] == "mybook.pdf"

        # 4. PATCH export updates
        resp = client.patch(
            f"/api/books/{book_id}/exports/{export_file['id']}",
            json={"status": "ready"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "ready"

        # 5. GET export bundle
        resp = client.get(f"/api/books/{book_id}/exports/bundle?run_id={run_id}")
        assert resp.status_code == 200, resp.text
        bundle = resp.json()
        assert bundle["total_files"] == 1
        assert bundle["ready_files"] == 1
        assert bundle["status"] == "ready"

        # 6. DELETE export record
        resp = client.delete(f"/api/books/{book_id}/exports/{export_file['id']}")
        assert resp.status_code == 200, resp.text

        # 7. GET deleted export returns 404
        resp = client.get(f"/api/books/{book_id}/exports/{export_file['id']}")
        assert resp.status_code == 404

    def test_post_export_for_missing_book_returns_404(self, client: TestClient):
        fake_book_id = str(uuid4())
        payload = {
            "book_id": fake_book_id,
            "export_type": "docx",
            "file_path": "/exports/b.docx",
            "file_name": "b.docx",
        }
        resp = client.post(f"/api/books/{fake_book_id}/exports", json=payload)
        assert resp.status_code == 404

    def test_export_request_creates_placeholders(self, client: TestClient):
        book_id = _create_book(client, "Export Request API Test")
        run_id = _create_run(client, book_id)

        # 1. POST exports/request
        req_payload = {
            "book_id": book_id,
            "run_id": run_id,
            "export_types": ["docx", "pdf", "prompt_dossier"],
        }
        resp = client.post(f"/api/books/{book_id}/exports/request", json=req_payload)
        assert resp.status_code == 200, resp.text
        result = resp.json()
        assert result["status"] == "accepted"
        assert len(result["created_files"]) == 3
        # Prove they are placeholders
        assert result["created_files"][0]["export_metadata"]["placeholder"] is True
        assert result["created_files"][0]["export_metadata"]["real_generation"] is False

    def test_list_run_exports(self, client: TestClient):
        book_id = _create_book(client, "Run Exports List Test")
        run_id = _create_run(client, book_id)

        # Seed an export file with run_id
        payload = {
            "book_id": book_id,
            "run_id": run_id,
            "export_type": "pdf",
            "file_path": "/exports/run.pdf",
            "file_name": "run.pdf",
        }
        resp = client.post(f"/api/books/{book_id}/exports", json=payload)
        assert resp.status_code == 201

        # GET /api/runs/{run_id}/exports
        resp = client.get(f"/api/runs/{run_id}/exports")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["file_name"] == "run.pdf"
