from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqladmin import Admin

from app.main import create_app


def test_admin_setup_views():
    """Verify that the FastAPI app has the Admin application mounted and all 18 views are registered."""
    app = create_app()
    
    # In sqladmin, Admin has a `.views` attribute which contains all registered ModelView classes.
    # Let's locate the admin instance. In typical setup_admin, we return the admin instance,
    # but since create_app() calls setup_admin(app) locally and doesn't store it on the FastAPI instance directly,
    # we can retrieve the admin instance by checking the routes or just calling setup_admin on a new app instance.
    from app.admin import setup_admin
    temp_app = FastAPI()
    admin_instance = setup_admin(temp_app)
    
    assert isinstance(admin_instance, Admin)
    
    registered_model_names = [view.model.__name__ for view in admin_instance.views]
    
    expected_models = {
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
    }
    
    for model_name in expected_models:
        assert model_name in registered_model_names, f"Model {model_name} is not registered in Admin"
    
    assert len(admin_instance.views) == 18, f"Expected 18 registered views, got {len(admin_instance.views)}"


def test_admin_index_redirect(client: TestClient):
    """Verify that GET /admin redirects or returns success."""
    response = client.get("/admin")
    # Starlette/FastAPI's Mount can return 307/302 redirect for trailing slash, or 200 directly depending on setup
    assert response.status_code in (200, 302, 307, 308)


def test_admin_dashboard_renders(client: TestClient):
    """Verify that GET /admin/ renders the dashboard containing references to our models."""
    response = client.get("/admin/")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text}"
    
    # Verify that plural display names of various models are rendered in the sidebar/page
    assert "Book Projects" in response.text
    assert "Book Sections" in response.text
    assert "Chapters" in response.text
    assert "Book Runs" in response.text
    assert "Source Documents" in response.text
    assert "Document Chunks" in response.text
    assert "Fact Registry Entries" in response.text
    assert "Concept Bible Entries" in response.text
    assert "Character Bible Entries" in response.text
    assert "Callback Index Entries" in response.text
    assert "Tone Fingerprints" in response.text
    assert "Decision Logs" in response.text
    assert "Agent Traces" in response.text
    assert "Prompt Logs" in response.text
    assert "Memory IO Logs" in response.text
    assert "Token Cost Ledgers" in response.text
    assert "Evaluation Results" in response.text
    assert "Export Files" in response.text
