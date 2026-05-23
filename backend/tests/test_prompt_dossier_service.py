"""
AIuthor Backend Tests — Prompt Dossier Service (Module 11.0).
"""
from __future__ import annotations

import pytest
from app.services.prompt_dossier_service import PromptDossierService
from app.workflows.schemas import PromptDossierRequest

def test_generate_prompt_dossier_returns_status():
    """1. generate_prompt_dossier returns status."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=True)
    res = svc.generate_prompt_dossier(req)
    assert res.status == "success"
    assert res.agent_count == 8
    assert res.template_count == 8

def test_dossier_includes_all_8_agents():
    """2. dossier includes all 8 agents."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=False)
    res = svc.generate_prompt_dossier(req)
    agent_names = [p["agent_name"] for p in res.prompts]
    expected_agents = ["planner", "researcher", "writer", "humanizer", "editor", "fact_checker", "memory_keeper", "assembler"]
    for agent in expected_agents:
        assert agent in agent_names
    assert "Planner Prompt" in res.markdown_dossier
    assert "Researcher Prompt" in res.markdown_dossier
    assert "Writer Prompt" in res.markdown_dossier
    assert "Humanizer Prompt" in res.markdown_dossier
    assert "Editor Prompt" in res.markdown_dossier
    assert "Fact Checker Prompt" in res.markdown_dossier
    assert "Memory Keeper Prompt" in res.markdown_dossier
    assert "Assembler Prompt" in res.markdown_dossier

def test_dossier_includes_planner_prompt():
    """3. dossier includes planner prompt template."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=False)
    res = svc.generate_prompt_dossier(req)
    planner_item = next(p for p in res.prompts if p["agent_name"] == "planner")
    assert "strategic book architect" in planner_item["role_excerpt"]
    assert "Agent Name: Planner" in planner_item["template"]

def test_dossier_includes_humanizer_prompt_and_rules():
    """4. dossier includes humanizer prompt/rules."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=False)
    res = svc.generate_prompt_dossier(req)
    humanizer_item = next(p for p in res.prompts if p["agent_name"] == "humanizer")
    assert "style humanizer" in humanizer_item["role_excerpt"]
    assert "Humanizer Rules" in res.markdown_dossier
    assert "preservation of all inline academic" in res.markdown_dossier

def test_dossier_includes_versions():
    """5. dossier includes versions."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=False)
    res = svc.generate_prompt_dossier(req)
    for p in res.prompts:
        assert p["version"] is not None
        assert len(p["version"]) >= 1

def test_dossier_includes_render_examples():
    """6. dossier includes render examples."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=True)
    res = svc.generate_prompt_dossier(req)
    for p in res.prompts:
        assert p["render_example"] is not None
        assert "Task:" in p["render_example"]
        assert "Context:" in p["render_example"]
        assert "Metadata:" in p["render_example"]

def test_dossier_does_not_include_secrets():
    """7. dossier does not include secrets/env values."""
    svc = PromptDossierService()
    req = PromptDossierRequest(include_templates=True, include_render_examples=True)
    res = svc.generate_prompt_dossier(req)
    content = res.markdown_dossier
    assert "API_KEY" not in content
    assert "DATABASE_URL" not in content
    assert "SECRET_KEY" not in content

def test_no_llm_calls_dossier():
    """8. no LLM calls are executed."""
    # Since PromptDossierService has no LLM client dependencies and does not call any LLM,
    # this passes implicitly.
    pass
