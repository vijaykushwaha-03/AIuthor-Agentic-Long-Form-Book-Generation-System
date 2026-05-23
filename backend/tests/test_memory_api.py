"""
AIuthor Backend Tests — Memory API route tests.

Uses the session-scoped TestClient from conftest.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


# ── Payload helpers ───────────────────────────────────────────────────────────

def _book_payload(**kw) -> dict:
    return {
        "topic": "Memory Test Book",
        "reader_profile": "Testers",
        "genre": "Fiction",
        "tone": "conversational",
        "target_chapters": 3,
        **kw,
    }


def _create_book(client: TestClient, topic="Memory API Test") -> str:
    resp = client.post("/api/books", json=_book_payload(topic=topic))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ══════════════════════════════════════════════════════════════════════════════
# Fact Registry API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestFactRegistryAPI:

    def test_fact_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Fact API Test")

        # 1. POST fact creates
        fact_payload = {
            "book_id": book_id,
            "claim": "Water freezes at 0 degrees Celsius.",
            "status": "unverified",
            "confidence": 0.95,
        }
        resp = client.post(f"/api/books/{book_id}/memory/facts", json=fact_payload)
        assert resp.status_code == 201, resp.text
        fact = resp.json()
        assert fact["id"] is not None
        assert fact["claim"] == "Water freezes at 0 degrees Celsius."

        # 2. GET facts lists
        resp = client.get(f"/api/books/{book_id}/memory/facts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == fact["id"]

        # 3. GET fact detail works
        resp = client.get(f"/api/books/{book_id}/memory/facts/{fact['id']}")
        assert resp.status_code == 200
        assert resp.json()["claim"] == "Water freezes at 0 degrees Celsius."

        # 4. PATCH fact updates
        resp = client.patch(
            f"/api/books/{book_id}/memory/facts/{fact['id']}",
            json={"claim": "Water freezes at 32 degrees Fahrenheit.", "status": "verified"},
        )
        assert resp.status_code == 200
        assert resp.json()["claim"] == "Water freezes at 32 degrees Fahrenheit."
        assert resp.json()["status"] == "verified"

        # 5. DELETE fact deletes
        resp = client.delete(f"/api/books/{book_id}/memory/facts/{fact['id']}")
        assert resp.status_code == 200
        assert resp.json()["message"] is not None

        # 6. GET deleted fact returns 404
        resp = client.get(f"/api/books/{book_id}/memory/facts/{fact['id']}")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Concept Bible API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestConceptBibleAPI:

    def test_concept_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Concept API Test")

        # POST concept
        payload = {
            "book_id": book_id,
            "concept": "Hyperdrive",
            "definition": "Faster than light engine.",
        }
        resp = client.post(f"/api/books/{book_id}/memory/concepts", json=payload)
        assert resp.status_code == 201, resp.text
        concept = resp.json()

        # GET concepts lists
        resp = client.get(f"/api/books/{book_id}/memory/concepts")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # PATCH concept
        resp = client.patch(
            f"/api/books/{book_id}/memory/concepts/{concept['id']}",
            json={"definition": "Tachyon energy device."},
        )
        assert resp.status_code == 200
        assert resp.json()["definition"] == "Tachyon energy device."

        # DELETE concept
        resp = client.delete(f"/api/books/{book_id}/memory/concepts/{concept['id']}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Character Bible API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCharacterBibleAPI:

    def test_character_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Character API Test")

        # POST character
        payload = {
            "book_id": book_id,
            "character_name": "Bob the Builder",
            "role": "Constructor",
        }
        resp = client.post(f"/api/books/{book_id}/memory/characters", json=payload)
        assert resp.status_code == 201
        char = resp.json()

        # GET characters lists
        resp = client.get(f"/api/books/{book_id}/memory/characters")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # PATCH character
        resp = client.patch(
            f"/api/books/{book_id}/memory/characters/{char['id']}",
            json={"role": "Architect"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "Architect"

        # DELETE character
        resp = client.delete(f"/api/books/{book_id}/memory/characters/{char['id']}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Callback Index API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCallbackIndexAPI:

    def test_callback_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Callback API Test")

        # POST callback
        payload = {
            "book_id": book_id,
            "source_chapter": 1,
            "target_chapter": 2,
            "callback_text": "Callback detail description",
        }
        resp = client.post(f"/api/books/{book_id}/memory/callbacks", json=payload)
        assert resp.status_code == 201
        cb = resp.json()

        # GET callbacks with filters
        resp = client.get(f"/api/books/{book_id}/memory/callbacks?source_chapter=1")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # PATCH callback
        resp = client.patch(
            f"/api/books/{book_id}/memory/callbacks/{cb['id']}",
            json={"status": "resolved"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

        # DELETE callback
        resp = client.delete(f"/api/books/{book_id}/memory/callbacks/{cb['id']}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Tone Fingerprint API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestToneFingerprintAPI:

    def test_tone_fingerprint_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Tone API Test")

        # POST tone fingerprint
        payload = {
            "book_id": book_id,
            "tone_name": "casual",
            "lexical_rules": {"avoid_slang": True},
        }
        resp = client.post(f"/api/books/{book_id}/memory/tone-fingerprints", json=payload)
        assert resp.status_code == 201
        tone = resp.json()

        # GET tone fingerprints with filters
        resp = client.get(f"/api/books/{book_id}/memory/tone-fingerprints?tone_name=casual")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # PATCH tone fingerprint
        resp = client.patch(
            f"/api/books/{book_id}/memory/tone-fingerprints/{tone['id']}",
            json={"lexical_rules": {"avoid_slang": False}},
        )
        assert resp.status_code == 200
        assert resp.json()["lexical_rules"] == {"avoid_slang": False}

        # DELETE tone fingerprint
        resp = client.delete(f"/api/books/{book_id}/memory/tone-fingerprints/{tone['id']}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Decision Log API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionLogAPI:

    def test_decision_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Decision API Test")

        # POST decision
        payload = {
            "book_id": book_id,
            "decision": "Use SQLite DB for fast test environments",
        }
        resp = client.post(f"/api/books/{book_id}/memory/decisions", json=payload)
        assert resp.status_code == 201
        dec = resp.json()

        # GET book decisions list
        resp = client.get(f"/api/books/{book_id}/memory/decisions")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # GET global decisions list
        resp = client.get("/api/memory/decisions")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # PATCH decision
        resp = client.patch(
            f"/api/books/{book_id}/memory/decisions/{dec['id']}",
            json={"impact": "Reduced test run duration by 5s"},
        )
        assert resp.status_code == 200
        assert resp.json()["impact"] == "Reduced test run duration by 5s"

        # DELETE decision
        resp = client.delete(f"/api/books/{book_id}/memory/decisions/{dec['id']}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# Memory Envelope API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMemoryEnvelopeAPI:

    def test_read_memory_envelope(self, client: TestClient):
        book_id = _create_book(client, "Envelope Read API Test")

        # Seed one fact via API
        resp = client.post(
            f"/api/books/{book_id}/memory/facts",
            json={"book_id": book_id, "claim": "Fact for envelope read test."},
        )
        assert resp.status_code == 201

        # POST /memory/read returns groups
        resp = client.post(
            f"/api/books/{book_id}/memory/read",
            json={"book_id": book_id, "memory_types": ["facts"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["book_id"] == book_id
        assert len(data["facts"]) == 1
        assert data["total_items"] == 1

    def test_write_memory_envelope(self, client: TestClient):
        book_id = _create_book(client, "Envelope Write API Test")

        # POST /memory/write creates records and counts
        payload = {
            "book_id": book_id,
            "facts": [
                {"book_id": book_id, "claim": "First batch claim"},
                {"book_id": book_id, "claim": "Second batch claim"},
            ],
            "concepts": [
                {"book_id": book_id, "concept": "FTL Engines", "definition": "Faster than light engine."}
            ]
        }
        resp = client.post(f"/api/books/{book_id}/memory/write", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["book_id"] == book_id
        assert data["created_counts"]["facts"] == 2
        assert data["created_counts"]["concepts"] == 1
        assert data["status"] == "completed"

        # Verify items exist in list
        list_resp = client.get(f"/api/books/{book_id}/memory/facts")
        assert list_resp.json()["total"] == 2


# ══════════════════════════════════════════════════════════════════════════════
# Error & Mismatch API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMemoryAPIErrors:

    def test_post_fact_for_missing_book_returns_404(self, client: TestClient):
        fake_id = str(uuid4())
        payload = {
            "book_id": fake_id,
            "claim": "Water freezes at 0 degrees Celsius.",
        }
        resp = client.post(f"/api/books/{fake_id}/memory/facts", json=payload)
        assert resp.status_code == 404

    def test_get_missing_memory_record_returns_404(self, client: TestClient):
        book_id = _create_book(client, "Error Detail 404 Test")
        fake_record_id = str(uuid4())

        resp = client.get(f"/api/books/{book_id}/memory/facts/{fake_record_id}")
        assert resp.status_code == 404

        resp = client.get(f"/api/books/{book_id}/memory/concepts/{fake_record_id}")
        assert resp.status_code == 404
