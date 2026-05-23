"""
AIuthor Backend Tests — BookProject and BookRun API route tests.

Uses the session-scoped TestClient from conftest.py.
Each test creates its own data to ensure independence.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ── Payload helpers ───────────────────────────────────────────────────────────

def _book_payload(**overrides) -> dict:
    defaults = {
        "topic": "Introduction to Machine Learning",
        "reader_profile": "Beginners with Python knowledge",
        "genre": "Technology",
        "tone": "conversational",
        "target_chapters": 10,
        "words_per_chapter": 2000,
    }
    defaults.update(overrides)
    return defaults


# ══════════════════════════════════════════════════════════════════════════════
# BookProject API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBookProjectAPI:

    def test_create_book_returns_201(self, client: TestClient):
        """POST /api/books returns HTTP 201 with book data."""
        response = client.post("/api/books", json=_book_payload())
        assert response.status_code == 201, response.text
        data = response.json()
        assert "id" in data
        assert data["topic"] == "Introduction to Machine Learning"
        assert data["status"] == "created"

    def test_list_books_returns_paginated_response(self, client: TestClient):
        """GET /api/books returns a paginated envelope."""
        # Create at least one book first
        client.post("/api/books", json=_book_payload(topic="List Test Book"))
        response = client.get("/api/books")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data
        assert data["total"] >= 1

    def test_get_book_returns_created_book(self, client: TestClient):
        """GET /api/books/{book_id} returns the created book."""
        created = client.post("/api/books", json=_book_payload(topic="Get Test Book"))
        book_id = created.json()["id"]

        response = client.get(f"/api/books/{book_id}")
        assert response.status_code == 200, response.text
        assert response.json()["id"] == book_id

    def test_get_missing_book_returns_404(self, client: TestClient):
        """GET /api/books/{unknown_id} returns 404."""
        from uuid import uuid4
        response = client.get(f"/api/books/{uuid4()}")
        assert response.status_code == 404

    def test_patch_book_updates_book(self, client: TestClient):
        """PATCH /api/books/{book_id} applies partial update."""
        created = client.post("/api/books", json=_book_payload(topic="Patch Source"))
        book_id = created.json()["id"]

        response = client.patch(
            f"/api/books/{book_id}", json={"topic": "Patch Destination"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["topic"] == "Patch Destination"

    def test_delete_book_returns_success(self, client: TestClient):
        """DELETE /api/books/{book_id} returns success message."""
        created = client.post("/api/books", json=_book_payload(topic="Delete Me"))
        book_id = created.json()["id"]

        response = client.delete(f"/api/books/{book_id}")
        assert response.status_code == 200, response.text
        assert response.json()["success"] is True

    def test_get_deleted_book_returns_404(self, client: TestClient):
        """After deletion, GET returns 404."""
        created = client.post("/api/books", json=_book_payload(topic="Delete Me 2"))
        book_id = created.json()["id"]
        client.delete(f"/api/books/{book_id}")

        response = client.get(f"/api/books/{book_id}")
        assert response.status_code == 404

    def test_list_books_filter_by_status(self, client: TestClient):
        """GET /api/books?status=created filters correctly."""
        client.post("/api/books", json=_book_payload(topic="Status Filter Book"))
        response = client.get("/api/books", params={"status": "created"})
        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "created" for item in data["items"])

    def test_list_books_search(self, client: TestClient):
        """GET /api/books?search=... filters by topic substring."""
        unique_topic = "Quantum Computing Fundamentals For Humans XYZ"
        client.post("/api/books", json=_book_payload(topic=unique_topic))
        response = client.get("/api/books", params={"search": "Quantum Computing"})
        assert response.status_code == 200
        assert response.json()["total"] >= 1
        topics = [item["topic"] for item in response.json()["items"]]
        assert any("Quantum Computing" in t for t in topics)


# ══════════════════════════════════════════════════════════════════════════════
# BookRun API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBookRunAPI:

    def _create_book(self, client: TestClient, topic="Run Test Book") -> str:
        """Helper: create a book and return its id."""
        resp = client.post("/api/books", json=_book_payload(topic=topic))
        assert resp.status_code == 201
        return resp.json()["id"]

    def _create_run(self, client: TestClient, book_id: str) -> str:
        """Helper: create a run and return its id."""
        resp = client.post(f"/api/books/{book_id}/runs")
        assert resp.status_code == 201, resp.text
        return resp.json()["id"]

    def test_create_run_returns_201_pending(self, client: TestClient):
        """POST /api/books/{book_id}/runs creates a pending run."""
        book_id = self._create_book(client, topic="Create Run Test")
        response = client.post(f"/api/books/{book_id}/runs")
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["status"] == "pending"
        assert data["book_id"] == book_id

    def test_list_runs_for_book(self, client: TestClient):
        """GET /api/books/{book_id}/runs returns paginated runs."""
        book_id = self._create_book(client, topic="List Runs Book")
        self._create_run(client, book_id)
        self._create_run(client, book_id)

        response = client.get(f"/api/books/{book_id}/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_get_run_returns_run_detail(self, client: TestClient):
        """GET /api/runs/{run_id} returns the run."""
        book_id = self._create_book(client, topic="Get Run Book")
        run_id = self._create_run(client, book_id)

        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        assert response.json()["id"] == run_id

    def test_get_missing_run_returns_404(self, client: TestClient):
        """GET /api/runs/{unknown_id} returns 404."""
        from uuid import uuid4
        response = client.get(f"/api/runs/{uuid4()}")
        assert response.status_code == 404

    def test_patch_run_updates_run(self, client: TestClient):
        """PATCH /api/runs/{run_id} applies partial update."""
        book_id = self._create_book(client, topic="Patch Run Book")
        run_id = self._create_run(client, book_id)

        response = client.patch(
            f"/api/runs/{run_id}", json={"status": "running", "current_agent": "planner"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["current_agent"] == "planner"

    def test_get_run_status_returns_status_envelope(self, client: TestClient):
        """GET /api/runs/{run_id}/status returns a monitoring envelope."""
        book_id = self._create_book(client, topic="Status Envelope Book")
        run_id = self._create_run(client, book_id)

        response = client.get(f"/api/runs/{run_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] == "pending"
        assert data["progress_percentage"] == 0.0
        assert "message" in data

    def test_start_run_marks_running(self, client: TestClient):
        """POST /api/runs/{run_id}/start transitions to status='running'."""
        book_id = self._create_book(client, topic="Start Run Book")
        run_id = self._create_run(client, book_id)

        response = client.post(f"/api/runs/{run_id}/start")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_complete_run_marks_completed(self, client: TestClient):
        """POST /api/runs/{run_id}/complete transitions to status='completed'."""
        book_id = self._create_book(client, topic="Complete Run Book")
        run_id = self._create_run(client, book_id)

        response = client.post(f"/api/runs/{run_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_fail_run_marks_failed(self, client: TestClient):
        """POST /api/runs/{run_id}/fail transitions to status='failed'."""
        book_id = self._create_book(client, topic="Fail Run Book")
        run_id = self._create_run(client, book_id)

        response = client.post(
            f"/api/runs/{run_id}/fail", json={"error_message": "Out of memory"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Out of memory"

    def test_create_run_for_missing_book_returns_404(self, client: TestClient):
        """POST /api/books/{unknown_id}/runs returns 404."""
        from uuid import uuid4
        response = client.post(f"/api/books/{uuid4()}/runs")
        assert response.status_code == 404

    def test_run_status_progress_running_is_50(self, client: TestClient):
        """Progress percentage for a running run is 50.0."""
        book_id = self._create_book(client, topic="Progress Book")
        run_id = self._create_run(client, book_id)
        client.post(f"/api/runs/{run_id}/start")

        status_resp = client.get(f"/api/runs/{run_id}/status")
        assert status_resp.json()["progress_percentage"] == 50.0

    def test_run_status_progress_completed_is_100(self, client: TestClient):
        """Progress percentage for a completed run is 100.0."""
        book_id = self._create_book(client, topic="Completed Progress Book")
        run_id = self._create_run(client, book_id)
        client.post(f"/api/runs/{run_id}/complete")

        status_resp = client.get(f"/api/runs/{run_id}/status")
        assert status_resp.json()["progress_percentage"] == 100.0
