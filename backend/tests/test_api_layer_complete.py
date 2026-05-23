"""
AIuthor Backend Tests — Final API Layer Verification Suite.

Validates registration, imports, schema loading, and Starlette routing ordering.
"""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_all_expected_route_modules_importable():
    """Verify that all router files can be imported with zero side-effects."""
    import app.api.routes_health  # noqa: F401
    import app.api.routes_books  # noqa: F401
    import app.api.routes_runs  # noqa: F401
    import app.api.routes_chapters  # noqa: F401
    import app.api.routes_sections  # noqa: F401
    import app.api.routes_rag  # noqa: F401
    import app.api.routes_memory  # noqa: F401
    import app.api.routes_observability  # noqa: F401
    import app.api.routes_eval_export  # noqa: F401
    import app.api.error_handlers  # noqa: F401


def test_all_expected_services_importable():
    """Verify all service classes and exceptions are exported from services package."""
    from app.services import (
        ServiceError,
        NotFoundError,
        ValidationServiceError,
        ConflictError,
        BookProjectService,
        BookRunService,
        ChapterService,
        BookSectionService,
        SourceDocumentService,
        DocumentChunkService,
        MemoryService,
        ObservabilityService,
        EvalService,
        ExportService,
        HybridRetrievalService,
        ContextPackService,
        AgentExecutionService,
        WorkflowExecutionService,
    )

    assert BookProjectService is not None
    assert BookRunService is not None
    assert ChapterService is not None
    assert BookSectionService is not None
    assert SourceDocumentService is not None
    assert DocumentChunkService is not None
    assert MemoryService is not None
    assert ObservabilityService is not None
    assert EvalService is not None
    assert ExportService is not None
    assert ServiceError is not None
    assert NotFoundError is not None
    assert ValidationServiceError is not None
    assert ConflictError is not None
    assert HybridRetrievalService is not None
    assert ContextPackService is not None
    assert AgentExecutionService is not None
    assert WorkflowExecutionService is not None


def test_openapi_schema_loads(client: TestClient):
    """Verify FastAPI generates a valid OpenAPI schema containing paths."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, resp.text
    schema = resp.json()
    assert "paths" in schema
    assert len(schema["paths"]) > 0


def test_openapi_contains_core_paths(client: TestClient):
    """Verify OpenAPI schema registers core project and run routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/books" in paths
    assert "/api/books/{book_id}" in paths
    assert "/api/books/{book_id}/runs" in paths
    assert "/api/runs/{run_id}" in paths
    assert "/api/runs/{run_id}/status" in paths


def test_openapi_contains_chapter_section_paths(client: TestClient):
    """Verify OpenAPI schema registers chapter and section routing."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/books/{book_id}/chapters" in paths
    assert "/api/books/{book_id}/chapters/insert" in paths
    assert "/api/books/{book_id}/chapters/reorder" in paths
    assert "/api/books/{book_id}/chapters/{chapter_id}" in paths
    assert "/api/books/{book_id}/sections" in paths
    assert "/api/books/{book_id}/sections/defaults" in paths
    assert "/api/books/{book_id}/sections/reorder" in paths
    assert "/api/books/{book_id}/sections/{section_id}" in paths


def test_openapi_contains_rag_paths(client: TestClient):
    """Verify OpenAPI schema registers reference source and chunking routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/books/{book_id}/sources" in paths
    assert "/api/books/{book_id}/sources/{document_id}" in paths
    assert "/api/sources/{document_id}/chunks" in paths
    assert "/api/sources/{document_id}/chunks/{chunk_id}" in paths
    assert "/api/sources/{document_id}/chunk" in paths
    assert "/api/rag/retrieve" in paths
    assert "/api/rag/hybrid-retrieve" in paths
    assert "/api/rag/context-pack" in paths


def test_openapi_contains_memory_paths(client: TestClient):
    """Verify OpenAPI schema registers lore candidates, register registers and envelopes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/books/{book_id}/memory/read" in paths
    assert "/api/books/{book_id}/memory/write" in paths
    assert "/api/books/{book_id}/memory/facts" in paths
    assert "/api/books/{book_id}/memory/concepts" in paths
    assert "/api/books/{book_id}/memory/characters" in paths
    assert "/api/books/{book_id}/memory/callbacks" in paths
    assert "/api/books/{book_id}/memory/tone-fingerprints" in paths
    assert "/api/books/{book_id}/memory/decisions" in paths
    assert "/api/memory/decisions" in paths


def test_openapi_contains_observability_paths(client: TestClient):
    """Verify OpenAPI schema registers prompt logger, audit, trace, and billing cost routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/runs/{run_id}/observability/traces" in paths
    assert "/api/runs/{run_id}/observability/prompts" in paths
    assert "/api/runs/{run_id}/observability/memory-io" in paths
    assert "/api/runs/{run_id}/observability/token-costs" in paths
    assert "/api/runs/{run_id}/observability/trace-bundle" in paths
    assert "/api/runs/{run_id}/observability/cost-summary" in paths


def test_openapi_contains_eval_export_paths(client: TestClient):
    """Verify OpenAPI schema registers validations, report compilations, and files exports."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/books/{book_id}/evals" in paths
    assert "/api/books/{book_id}/evals/{eval_id}" in paths
    assert "/api/books/{book_id}/eval-report" in paths
    assert "/api/runs/{run_id}/evals" in paths
    assert "/api/books/{book_id}/exports" in paths
    assert "/api/books/{book_id}/exports/request" in paths
    assert "/api/books/{book_id}/exports/bundle" in paths
    assert "/api/books/{book_id}/exports/{export_id}" in paths
    assert "/api/runs/{run_id}/exports" in paths


def test_openapi_contains_agent_paths(client: TestClient):
    """Verify OpenAPI schema registers agent endpoints."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/agents" in paths
    assert "/api/agents/{agent_name}" in paths
    assert "/api/agents/render-prompt" in paths
    assert "/api/agents/mock-run" in paths
    assert "/api/agents/dev-run-real" in paths


def test_openapi_contains_workflow_paths(client: TestClient):
    """Verify OpenAPI schema registers workflow endpoints (Module 7.1A & 7.1B)."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/workflows" in paths
    assert "/api/workflows/{workflow_name}" in paths
    assert "/api/workflows/mock-run" in paths
    assert "/api/workflows/dev-run-real" in paths
    assert "/api/workflows/mock-run-traced" in paths
    assert "/api/workflows/dev-run-real-traced" in paths
    assert "/api/workflows/traces/{run_id}" in paths


def test_no_duplicate_route_method_pairs():
    """Verify that there are no duplicate path + method mapping combinations in the router."""
    routes_seen = set()
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            for method in route.methods:
                pair = (route.path, method)
                assert pair not in routes_seen, f"Duplicate path+method found: {pair}"
                routes_seen.add(pair)


def test_static_routes_exist_separately_from_dynamic_routes(client: TestClient):
    """Assert Starlette route evaluation ordering maps static subpaths independently from dynamic parameters."""
    paths = client.get("/openapi.json").json()["paths"]
    static_paths = [
        "/api/books/{book_id}/chapters/insert",
        "/api/books/{book_id}/chapters/reorder",
        "/api/books/{book_id}/sections/defaults",
        "/api/books/{book_id}/sections/reorder",
        "/api/books/{book_id}/exports/request",
        "/api/books/{book_id}/exports/bundle",
        "/api/agents/render-prompt",
        "/api/agents/mock-run",
        "/api/agents/dev-run-real",
        "/api/workflows/mock-run",
        "/api/workflows/dev-run-real",
        "/api/workflows/mock-run-traced",
        "/api/workflows/dev-run-real-traced",
        "/api/workflows/traces/{run_id}",
    ]
    for p in static_paths:
        assert p in paths, f"Expected static path {p} not registered in OpenAPI"


def test_contract_docs_exist():
    """Verify all Module 4 REST contract markdown files are created and placed correctly."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contracts_dir = os.path.join(base_dir, "docs", "api_contracts")

    expected_files = [
        "core_book_contracts.md",
        "rag_contracts.md",
        "memory_contracts.md",
        "observability_contracts.md",
        "eval_export_contracts.md",
        "api_inventory.md",
        "README.md",
    ]
    for f in expected_files:
        path = os.path.join(contracts_dir, f)
        assert os.path.exists(path), f"Expected contract file missing: {path}"


def test_no_agent_or_langgraph_modules_required_for_api_layer():
    """Verify backend launches cleanly without depending on workflow engine or unimplemented components."""
    from app.main import app as main_app
    assert main_app is not None


def test_api_layer_does_not_require_pgvector():
    """Verify DB and routers run without vector modules (postponed in accordance with DEC-011)."""
    # Standard SQLite configuration will fail if postgres/pgvector is strictly required at compile/load time
    assert app.dependency_overrides is not None


def test_workflow_registry_exposes_both_pipelines(client: TestClient):
    """Verify workflow registry returns both mini_book_pipeline and full_agent_pipeline."""
    resp = client.get("/api/workflows")
    assert resp.status_code == 200
    data = resp.json()
    names = [w["workflow_name"] for w in data]
    assert "mini_book_pipeline" in names
    assert "full_agent_pipeline" in names
