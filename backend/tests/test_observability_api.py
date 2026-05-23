"""
AIuthor Backend Tests — Observability API Route Tests.

Uses the session-scoped TestClient from conftest.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


# ── Payload helpers ───────────────────────────────────────────────────────────

def _book_payload(**kw) -> dict:
    return {
        "topic": "Observability Test Book",
        "reader_profile": "Testers",
        "genre": "Fiction",
        "tone": "conversational",
        "target_chapters": 3,
        **kw,
    }


def _create_book(client: TestClient, topic="Observability API Test") -> str:
    resp = client.post("/api/books", json=_book_payload(topic=topic))
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_run(client: TestClient, book_id: str) -> str:
    resp = client.post(f"/api/books/{book_id}/runs", json={"book_id": book_id, "run_metadata": {"env": "test"}})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ══════════════════════════════════════════════════════════════════════════════
# Agent Trace API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentTraceAPI:

    def test_trace_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Trace Lifecycle API Test")
        run_id = _create_run(client, book_id)

        # 1. POST trace creates
        payload = {
            "run_id": run_id,
            "book_id": book_id,
            "agent_name": "planner",
            "status": "started",
            "input_summary": "Initial planning phase.",
        }
        resp = client.post(f"/api/runs/{run_id}/observability/traces", json=payload)
        assert resp.status_code == 201, resp.text
        trace = resp.json()
        assert trace["id"] is not None
        assert trace["agent_name"] == "planner"
        assert trace["status"] == "started"

        # 2. GET traces lists
        resp = client.get(f"/api/runs/{run_id}/observability/traces")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == trace["id"]

        # 3. GET trace detail works
        resp = client.get(f"/api/observability/traces/{trace['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["agent_name"] == "planner"

        # 4. PATCH trace updates
        resp = client.patch(
            f"/api/observability/traces/{trace['id']}",
            json={"status": "completed", "output_summary": "Planning completed successfully."},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"
        assert resp.json()["output_summary"] == "Planning completed successfully."

        # 5. DELETE trace deletes
        resp = client.delete(f"/api/observability/traces/{trace['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["message"] is not None

        # 6. GET deleted trace returns 404
        resp = client.get(f"/api/observability/traces/{trace['id']}")
        assert resp.status_code == 404

    def test_post_trace_for_missing_run_returns_404(self, client: TestClient):
        book_id = _create_book(client, "Missing Run Trace Test")
        fake_run_id = str(uuid4())
        payload = {
            "run_id": fake_run_id,
            "book_id": book_id,
            "agent_name": "planner",
            "status": "started",
        }
        resp = client.post(f"/api/runs/{fake_run_id}/observability/traces", json=payload)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Prompt Log API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptLogAPI:

    def test_prompt_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Prompt Lifecycle API Test")
        run_id = _create_run(client, book_id)

        # 1. POST prompt log
        payload = {
            "run_id": run_id,
            "book_id": book_id,
            "agent_name": "researcher",
            "model_name": "gpt-4o",
            "prompt_name": "gather_facts",
            "prompt_text": "Write a descriptive outline about Mars.",
            "input_payload": {"topic": "Mars"},
        }
        resp = client.post(f"/api/runs/{run_id}/observability/prompts", json=payload)
        assert resp.status_code == 201, resp.text
        log = resp.json()
        assert log["id"] is not None
        assert log["prompt_text"] == "Write a descriptive outline about Mars."

        # 2. GET prompts lists
        resp = client.get(f"/api/runs/{run_id}/observability/prompts?model_name=gpt-4o")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == log["id"]

        # 3. GET prompt log detail
        resp = client.get(f"/api/observability/prompts/{log['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["prompt_name"] == "gather_facts"

        # 4. PATCH prompt log updates
        resp = client.patch(
            f"/api/observability/prompts/{log['id']}",
            json={"output_payload": {"response": "Mars is red."}},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["output_payload"] == {"response": "Mars is red."}

        # 5. DELETE prompt log deletes
        resp = client.delete(f"/api/observability/prompts/{log['id']}")
        assert resp.status_code == 200, resp.text

        # 6. GET deleted prompt returns 404
        resp = client.get(f"/api/observability/prompts/{log['id']}")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Memory I/O Log API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMemoryIOLogAPI:

    def test_memory_io_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Memory IO Lifecycle API Test")
        run_id = _create_run(client, book_id)

        # 1. POST memory IO log
        payload = {
            "run_id": run_id,
            "book_id": book_id,
            "agent_name": "memory_keeper",
            "operation": "write",
            "memory_type": "concept_bible",
            "payload": {"key": "value"},
        }
        resp = client.post(f"/api/runs/{run_id}/observability/memory-io", json=payload)
        assert resp.status_code == 201, resp.text
        log = resp.json()
        assert log["id"] is not None
        assert log["memory_type"] == "concept_bible"

        # 2. GET memory IO logs list
        resp = client.get(f"/api/runs/{run_id}/observability/memory-io?operation=write")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == log["id"]

        # 3. GET memory IO log detail
        resp = client.get(f"/api/observability/memory-io/{log['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["memory_type"] == "concept_bible"

        # 4. DELETE memory IO log deletes
        resp = client.delete(f"/api/observability/memory-io/{log['id']}")
        assert resp.status_code == 200, resp.text

        # 5. GET deleted memory IO returns 404
        resp = client.get(f"/api/observability/memory-io/{log['id']}")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Token Cost Ledger API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenCostLedgerAPI:

    def test_token_cost_lifecycle(self, client: TestClient):
        book_id = _create_book(client, "Token Cost Lifecycle API Test")
        run_id = _create_run(client, book_id)

        # 1. POST token cost
        payload = {
            "run_id": run_id,
            "book_id": book_id,
            "agent_name": "writer",
            "model_name": "gpt-4o-mini",
            "input_tokens": 100,
            "output_tokens": 50,
            "estimated_cost": 0.005,
        }
        resp = client.post(f"/api/runs/{run_id}/observability/token-costs", json=payload)
        assert resp.status_code == 201, resp.text
        cost = resp.json()
        assert cost["id"] is not None
        assert cost["total_tokens"] == 150

        # 2. GET token costs lists
        resp = client.get(f"/api/runs/{run_id}/observability/token-costs?model_name=gpt-4o-mini")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["id"] == cost["id"]

        # 3. GET token cost detail
        resp = client.get(f"/api/observability/token-costs/{cost['id']}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["model_name"] == "gpt-4o-mini"

        # 4. PATCH token cost updates
        resp = client.patch(
            f"/api/observability/token-costs/{cost['id']}",
            json={"input_tokens": 200},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["total_tokens"] == 250

        # 5. DELETE token cost deletes
        resp = client.delete(f"/api/observability/token-costs/{cost['id']}")
        assert resp.status_code == 200, resp.text

        # 6. GET deleted token cost returns 404
        resp = client.get(f"/api/observability/token-costs/{cost['id']}")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Bundle and Summary API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestObservabilityBundlesAPI:

    def test_trace_bundle_and_cost_summary(self, client: TestClient):
        book_id = _create_book(client, "Bundles API Test")
        run_id = _create_run(client, book_id)

        # Seed some data via API
        resp = client.post(
            f"/api/runs/{run_id}/observability/traces",
            json={"run_id": run_id, "agent_name": "planner", "status": "started"},
        )
        assert resp.status_code == 201

        resp = client.post(
            f"/api/runs/{run_id}/observability/prompts",
            json={"run_id": run_id, "agent_name": "researcher", "prompt_text": "Sample prompt"},
        )
        assert resp.status_code == 201

        resp = client.post(
            f"/api/runs/{run_id}/observability/memory-io",
            json={"run_id": run_id, "operation": "write", "memory_type": "concept"},
        )
        assert resp.status_code == 201

        resp = client.post(
            f"/api/runs/{run_id}/observability/token-costs",
            json={"run_id": run_id, "model_name": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "estimated_cost": 0.02},
        )
        assert resp.status_code == 201

        # 1. GET trace-bundle
        resp = client.get(f"/api/runs/{run_id}/observability/trace-bundle")
        assert resp.status_code == 200, resp.text
        bundle = resp.json()
        assert bundle["run_id"] == run_id
        assert bundle["total_trace_records"] == 1
        assert bundle["total_prompt_logs"] == 1
        assert bundle["total_memory_io_records"] == 1
        assert bundle["total_token_cost_records"] == 1
        assert bundle["status"] == "ready"

        # 2. GET cost-summary
        resp = client.get(f"/api/runs/{run_id}/observability/cost-summary")
        assert resp.status_code == 200, resp.text
        summary = resp.json()
        assert summary["run_id"] == run_id
        assert summary["total_input_tokens"] == 100
        assert summary["total_output_tokens"] == 50
        assert summary["total_tokens"] == 150
        assert float(summary["total_estimated_cost"]) == 0.02
        assert "gpt-4o" in summary["model_breakdown"]


# ══════════════════════════════════════════════════════════════════════════════
# Error Details API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestObservabilityErrorsAPI:

    def test_get_missing_trace_returns_404(self, client: TestClient):
        resp = client.get(f"/api/observability/traces/{uuid4()}")
        assert resp.status_code == 404

    def test_get_missing_prompt_returns_404(self, client: TestClient):
        resp = client.get(f"/api/observability/prompts/{uuid4()}")
        assert resp.status_code == 404

    def test_get_missing_memory_io_returns_404(self, client: TestClient):
        resp = client.get(f"/api/observability/memory-io/{uuid4()}")
        assert resp.status_code == 404

    def test_get_missing_token_cost_returns_404(self, client: TestClient):
        resp = client.get(f"/api/observability/token-costs/{uuid4()}")
        assert resp.status_code == 404
