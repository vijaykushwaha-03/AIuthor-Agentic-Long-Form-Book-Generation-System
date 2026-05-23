"""
AIuthor Backend Tests — Chapter and BookSection API route tests.

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
    }
    defaults.update(overrides)
    return defaults


def _chapter_payload(book_id: str, number: int = 1, **overrides) -> dict:
    defaults = {
        "book_id": book_id,
        "chapter_number": number,
        "title": f"Chapter {number}: Understanding Core Concepts",
        "summary": "A comprehensive overview of core concepts.",
    }
    defaults.update(overrides)
    return defaults


def _section_payload(book_id: str, sort_order: int = 0, **overrides) -> dict:
    defaults = {
        "book_id": book_id,
        "section_type": "toc",
        "sort_order": sort_order,
    }
    defaults.update(overrides)
    return defaults


def _create_book(client: TestClient, topic="API Test Book") -> str:
    resp = client.post("/api/books", json=_book_payload(topic=topic))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ══════════════════════════════════════════════════════════════════════════════
# Chapter API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestChapterAPI:

    def test_create_chapter_returns_201(self, client: TestClient):
        """POST /api/books/{book_id}/chapters returns 201 with chapter data."""
        book_id = _create_book(client, topic="Create Chapter Book")
        response = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["chapter_number"] == 1
        assert data["book_id"] == book_id
        assert data["status"] == "planned"

    def test_list_chapters_returns_paginated_response(self, client: TestClient):
        """GET /api/books/{book_id}/chapters returns paginated envelope."""
        book_id = _create_book(client, topic="List Chapters Book")
        client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        response = client.get(f"/api/books/{book_id}/chapters")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 1

    def test_get_chapter_returns_chapter_detail(self, client: TestClient):
        """GET /api/books/{book_id}/chapters/{chapter_id} returns full detail."""
        book_id = _create_book(client, topic="Get Chapter Book")
        created = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        chapter_id = created.json()["id"]
        response = client.get(f"/api/books/{book_id}/chapters/{chapter_id}")
        assert response.status_code == 200, response.text
        assert response.json()["id"] == chapter_id

    def test_patch_chapter_updates_chapter(self, client: TestClient):
        """PATCH /api/books/{book_id}/chapters/{chapter_id} applies partial update."""
        book_id = _create_book(client, topic="Patch Chapter Book")
        created = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        chapter_id = created.json()["id"]
        response = client.patch(
            f"/api/books/{book_id}/chapters/{chapter_id}",
            json={"summary": "Updated summary text"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["summary"] == "Updated summary text"

    def test_delete_chapter_returns_success(self, client: TestClient):
        """DELETE /api/books/{book_id}/chapters/{chapter_id} returns success."""
        book_id = _create_book(client, topic="Delete Chapter Book")
        created = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        chapter_id = created.json()["id"]
        response = client.delete(f"/api/books/{book_id}/chapters/{chapter_id}")
        assert response.status_code == 200, response.text
        assert response.json()["success"] is True

    def test_get_deleted_chapter_returns_404(self, client: TestClient):
        """After deletion, GET returns 404."""
        book_id = _create_book(client, topic="Deleted Chapter 404 Book")
        created = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        chapter_id = created.json()["id"]
        client.delete(f"/api/books/{book_id}/chapters/{chapter_id}")
        response = client.get(f"/api/books/{book_id}/chapters/{chapter_id}")
        assert response.status_code == 404

    def test_duplicate_chapter_number_returns_409(self, client: TestClient):
        """Creating a chapter with a duplicate chapter_number returns 409."""
        book_id = _create_book(client, topic="Conflict Chapter Book")
        client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        response = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        assert response.status_code == 409, response.text

    def test_create_chapter_for_missing_book_returns_404(self, client: TestClient):
        """POST chapter for a non-existent book returns 404."""
        from uuid import uuid4
        response = client.post(
            f"/api/books/{uuid4()}/chapters",
            json=_chapter_payload(str(uuid4()), number=1),
        )
        assert response.status_code == 404

    def test_insert_chapter_creates_chapter(self, client: TestClient):
        """POST /api/books/{book_id}/chapters/insert creates an inserted chapter."""
        book_id = _create_book(client, topic="Insert Chapter Book")
        response = client.post(
            f"/api/books/{book_id}/chapters/insert",
            json={
                "after_chapter": 0,
                "title": "New First Chapter",
                "purpose": "Covers foundational topics before anything else",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["chapter_number"] == 1

    def test_insert_chapter_shifts_later_chapter_numbers(self, client: TestClient):
        """Inserting shifts later chapters by +1."""
        book_id = _create_book(client, topic="Insert Shift Book")
        # Create chapters 1 and 2
        ch1_resp = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        ch2_resp = client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=2),
        )
        ch2_id = ch2_resp.json()["id"]

        # Insert after chapter 1 (should shift chapter 2 → 3)
        client.post(
            f"/api/books/{book_id}/chapters/insert",
            json={
                "after_chapter": 1,
                "title": "Inserted between 1 and 2",
                "purpose": "Bridging content",
            },
        )

        # Fetch original chapter 2 — should now be chapter 3
        fetched = client.get(f"/api/books/{book_id}/chapters/{ch2_id}")
        assert fetched.json()["chapter_number"] == 3

    def test_insert_chapter_marks_repair_required(self, client: TestClient):
        """Inserted chapter has repair_required=True in chapter_contract."""
        book_id = _create_book(client, topic="Repair Flag Book")
        response = client.post(
            f"/api/books/{book_id}/chapters/insert",
            json={
                "after_chapter": 0,
                "title": "Repair Test Chapter",
                "purpose": "Testing the repair flag",
            },
        )
        assert response.status_code == 201, response.text
        contract = response.json().get("chapter_contract", {})
        assert contract.get("repair_required") is True

    def test_reorder_chapters_returns_ordered_list(self, client: TestClient):
        """POST /api/books/{book_id}/chapters/reorder returns renumbered list."""
        book_id = _create_book(client, topic="Reorder Book")
        client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=1),
        )
        client.post(
            f"/api/books/{book_id}/chapters",
            json=_chapter_payload(book_id, number=3),
        )
        response = client.post(f"/api/books/{book_id}/chapters/reorder")
        assert response.status_code == 200, response.text
        numbers = [c["chapter_number"] for c in response.json()]
        assert numbers == sorted(numbers)
        assert numbers == list(range(1, len(numbers) + 1))


# ══════════════════════════════════════════════════════════════════════════════
# BookSection API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBookSectionAPI:

    def test_create_section_returns_201(self, client: TestClient):
        """POST /api/books/{book_id}/sections returns 201 with section data."""
        book_id = _create_book(client, topic="Create Section Book")
        response = client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=0),
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["section_type"] == "toc"
        assert data["book_id"] == book_id
        assert data["status"] == "draft"

    def test_list_sections_returns_sections(self, client: TestClient):
        """GET /api/books/{book_id}/sections lists all sections."""
        book_id = _create_book(client, topic="List Sections Book")
        client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=0),
        )
        response = client.get(f"/api/books/{book_id}/sections")
        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_section_returns_section_detail(self, client: TestClient):
        """GET /api/books/{book_id}/sections/{section_id} returns full detail."""
        book_id = _create_book(client, topic="Get Section Book")
        created = client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=0),
        )
        section_id = created.json()["id"]
        response = client.get(f"/api/books/{book_id}/sections/{section_id}")
        assert response.status_code == 200, response.text
        assert response.json()["id"] == section_id

    def test_patch_section_updates_section(self, client: TestClient):
        """PATCH /api/books/{book_id}/sections/{section_id} applies partial update."""
        book_id = _create_book(client, topic="Patch Section Book")
        created = client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=0),
        )
        section_id = created.json()["id"]
        response = client.patch(
            f"/api/books/{book_id}/sections/{section_id}",
            json={"content": "Rendered table of contents goes here."},
        )
        assert response.status_code == 200, response.text
        assert response.json()["content"] == "Rendered table of contents goes here."

    def test_delete_section_returns_success(self, client: TestClient):
        """DELETE /api/books/{book_id}/sections/{section_id} returns success."""
        book_id = _create_book(client, topic="Delete Section Book")
        created = client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=0),
        )
        section_id = created.json()["id"]
        response = client.delete(f"/api/books/{book_id}/sections/{section_id}")
        assert response.status_code == 200, response.text
        assert response.json()["success"] is True

    def test_get_deleted_section_returns_404(self, client: TestClient):
        """After deletion, GET returns 404."""
        book_id = _create_book(client, topic="Deleted Section 404 Book")
        created = client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=0),
        )
        section_id = created.json()["id"]
        client.delete(f"/api/books/{book_id}/sections/{section_id}")
        response = client.get(f"/api/books/{book_id}/sections/{section_id}")
        assert response.status_code == 404

    def test_create_section_for_missing_book_returns_404(self, client: TestClient):
        """POST section for a non-existent book returns 404."""
        from uuid import uuid4
        fake_id = str(uuid4())
        response = client.post(
            f"/api/books/{fake_id}/sections",
            json=_section_payload(fake_id, sort_order=0),
        )
        assert response.status_code == 404

    def test_defaults_creates_front_and_back_matter(self, client: TestClient):
        """POST /api/books/{book_id}/sections/defaults creates required sections."""
        book_id = _create_book(client, topic="Defaults Section Book")
        response = client.post(f"/api/books/{book_id}/sections/defaults")
        assert response.status_code == 200, response.text
        data = response.json()
        section_types = {s["section_type"] for s in data}
        # Check a sample from front matter and back matter
        assert "toc" in section_types
        assert "glossary" in section_types
        assert "about_author" in section_types

    def test_defaults_does_not_duplicate_sections(self, client: TestClient):
        """Calling defaults twice does not duplicate section_types."""
        book_id = _create_book(client, topic="Idempotent Defaults Book")
        first = client.post(f"/api/books/{book_id}/sections/defaults")
        second = client.post(f"/api/books/{book_id}/sections/defaults")

        first_types = [s["section_type"] for s in first.json()]
        second_types = [s["section_type"] for s in second.json()]

        # Counts should be identical (no new sections added on second call)
        assert len(first_types) == len(second_types)
        # No duplicates in second call
        assert len(second_types) == len(set(second_types))

    def test_reorder_sections_returns_sequential_sort_order(self, client: TestClient):
        """POST /api/books/{book_id}/sections/reorder returns sequential sort_order."""
        book_id = _create_book(client, topic="Reorder Sections Book")
        client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=10, section_type="toc"),
        )
        client.post(
            f"/api/books/{book_id}/sections",
            json=_section_payload(book_id, sort_order=20, section_type="preface"),
        )
        response = client.post(f"/api/books/{book_id}/sections/reorder")
        assert response.status_code == 200, response.text
        orders = [s["sort_order"] for s in response.json()]
        assert orders == sorted(orders)
        assert orders == list(range(len(orders)))
