"""
AIuthor Backend Tests — Agent Prompt Registry Verification (Module 7.0A).
"""
from __future__ import annotations

import pytest
from app.agents.prompt_registry import PromptRegistry
from app.agents.exceptions import AgentPromptError


def test_prompt_registry_lists_all_eight_templates():
    """Verify that PromptRegistry lists exactly the 8 core agent templates."""
    registry = PromptRegistry()
    templates = registry.list_templates()
    expected = [
        "assembler",
        "editor",
        "fact_checker",
        "humanizer",
        "memory_keeper",
        "planner",
        "researcher",
        "writer",
    ]
    assert templates == expected


def test_each_required_agent_template_exists():
    """Verify that each expected prompt template file exists."""
    registry = PromptRegistry()
    expected = [
        "assembler",
        "editor",
        "fact_checker",
        "humanizer",
        "memory_keeper",
        "planner",
        "researcher",
        "writer",
    ]
    for agent_name in expected:
        content = registry.get_template(agent_name)
        assert content is not None
        assert len(content) > 0


def test_get_template_returns_non_empty_text():
    """Verify get_template retrieves the file text successfully."""
    registry = PromptRegistry()
    text = registry.get_template("planner")
    assert "Planner" in text
    assert len(text.strip()) > 0


def test_get_version_returns_v1():
    """Verify get_version correctly parses the Version header from markdown templates."""
    registry = PromptRegistry()
    expected = [
        "assembler",
        "editor",
        "fact_checker",
        "humanizer",
        "memory_keeper",
        "planner",
        "researcher",
        "writer",
    ]
    for name in expected:
        version = registry.get_version(name)
        assert version == "v1"


def test_render_prompt_returns_system_and_user_prompts():
    """Verify render_prompt compiles system and user prompt strings correctly."""
    registry = PromptRegistry()
    system_prompt, user_prompt = registry.render_prompt(
        agent_name="planner",
        task="Write a Sci-Fi story outline",
        context={"number_of_chapters": 5},
        metadata={"user_tier": "premium"},
    )
    assert system_prompt == registry.get_template("planner")
    assert user_prompt is not None
    assert "Task:\nWrite a Sci-Fi story outline" in user_prompt


def test_render_prompt_includes_task():
    """Verify rendered user prompt includes the task parameter value."""
    registry = PromptRegistry()
    _, user_prompt = registry.render_prompt(
        agent_name="researcher",
        task="Verify the population of Mars",
    )
    assert "Verify the population of Mars" in user_prompt


def test_render_prompt_includes_serialized_context():
    """Verify rendered user prompt includes the deterministic serialized context dictionary."""
    registry = PromptRegistry()
    _, user_prompt = registry.render_prompt(
        agent_name="writer",
        task="Draft chapter 1",
        context={"chapter_id": 1, "status": "pending"},
    )
    assert '"chapter_id": 1' in user_prompt
    assert '"status": "pending"' in user_prompt


def test_missing_template_raises_agent_prompt_error():
    """Verify retrieving a non-existent template raises an AgentPromptError exception."""
    registry = PromptRegistry()
    with pytest.raises(AgentPromptError) as exc_info:
        registry.get_template("non_existent_agent")
    assert "not found" in str(exc_info.value)
    assert exc_info.value.agent_name == "non_existent_agent"


def test_each_template_contains_agent_name():
    """Verify that every markdown template includes its specific 'Agent Name' declaration."""
    registry = PromptRegistry()
    agents = registry.list_templates()
    for name in agents:
        content = registry.get_template(name)
        assert "Agent Name:" in content or "Agent name:" in content


def test_each_template_contains_version_v1():
    """Verify that every markdown template declares its version line as 'Version: v1'."""
    registry = PromptRegistry()
    agents = registry.list_templates()
    for name in agents:
        content = registry.get_template(name)
        assert "Version: v1" in content


def test_each_template_contains_role_section():
    """Verify that every markdown template has a defined 'Role' section."""
    registry = PromptRegistry()
    agents = registry.list_templates()
    for name in agents:
        content = registry.get_template(name)
        assert "Role:" in content


def test_each_template_contains_output_contract_section():
    """Verify that every markdown template specifies an 'Output Contract' section."""
    registry = PromptRegistry()
    agents = registry.list_templates()
    for name in agents:
        content = registry.get_template(name)
        assert "Output Contract:" in content
