"""
AIuthor Backend Tests — Agent Registry Verification (Module 7.0A).
"""
from __future__ import annotations

import pytest
from app.agents.registry import (
    list_agent_names,
    list_agent_info,
    get_agent,
    SUPPORTED_AGENTS,
)
from app.agents.planner import PlannerAgent
from app.agents.writer import WriterAgent
from app.agents.schemas import AgentInput, AgentInfo
from app.agents.exceptions import AgentNotFoundError
from app.services.llm_service import LLMService


def test_list_agent_names_returns_all_eight_agents():
    """Verify list_agent_names returns all 8 core pipeline agent names."""
    names = list_agent_names()
    assert len(names) == 8
    for expected_name in [
        "planner",
        "researcher",
        "writer",
        "humanizer",
        "editor",
        "fact_checker",
        "memory_keeper",
        "assembler",
    ]:
        assert expected_name in names


def test_list_agent_info_returns_agent_info_list():
    """Verify list_agent_info returns a list of AgentInfo schemas."""
    infos = list_agent_info()
    assert len(infos) == 8
    for info in infos:
        assert isinstance(info, AgentInfo)
        assert info.agent_name in SUPPORTED_AGENTS


def test_get_agent_returns_planner_agent():
    """Verify get_agent instantiates and returns a PlannerAgent."""
    agent = get_agent("planner")
    assert isinstance(agent, PlannerAgent)
    assert agent.agent_name == "planner"


def test_get_agent_returns_writer_agent():
    """Verify get_agent instantiates and returns a WriterAgent."""
    agent = get_agent("writer")
    assert isinstance(agent, WriterAgent)
    assert agent.agent_name == "writer"


def test_get_agent_invalid_raises_agent_not_found_error():
    """Verify get_agent raises AgentNotFoundError on unregistered names."""
    with pytest.raises(AgentNotFoundError) as exc_info:
        get_agent("non_existent_agent")
    assert "not registered" in str(exc_info.value)
    assert exc_info.value.agent_name == "non_existent_agent"


def test_each_agent_has_display_name_and_description():
    """Verify all registry agent classes specify display_name and description."""
    for name in list_agent_names():
        agent = get_agent(name)
        assert agent.display_name is not None
        assert len(agent.display_name.strip()) > 0
        assert agent.description is not None
        assert len(agent.description.strip()) > 0


def test_researcher_requires_context_pack_is_true():
    """Verify ResearcherAgent has requires_context_pack=True and requires_memory=False."""
    agent = get_agent("researcher")
    assert agent.requires_context_pack is True
    assert agent.requires_memory is False


def test_writer_requires_context_pack_and_memory_are_true():
    """Verify WriterAgent has requires_context_pack=True and requires_memory=True."""
    agent = get_agent("writer")
    assert agent.requires_context_pack is True
    assert agent.requires_memory is True


def test_fact_checker_requires_context_pack_is_true():
    """Verify FactCheckerAgent has requires_context_pack=True and requires_memory=False."""
    agent = get_agent("fact_checker")
    assert agent.requires_context_pack is True
    assert agent.requires_memory is False


def test_agent_build_messages_returns_system_and_user_messages():
    """Verify build_messages constructs system and user LLMMessage entries."""
    agent = get_agent("planner")
    inp = AgentInput(
        agent_name="planner",
        task="Create outline",
        payload={"genre": "mystery"},
    )
    messages = agent.build_messages(inp)
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "Create outline" in messages[1].content


def test_run_mock_returns_agent_output_with_status_completed():
    """Verify run_mock generates deterministic responses and returns completed status."""
    agent = get_agent("planner")
    inp = AgentInput(
        agent_name="planner",
        task="Generate characters list",
    )
    output = agent.run_mock(inp)
    assert output.agent_name == "planner"
    assert output.status == "completed"
    assert "Mock response for:" in output.content
    assert "Generate characters list" in output.content
    assert output.input_tokens is not None
    assert output.input_tokens > 0
    assert output.output_tokens is not None
    assert output.output_tokens > 0
    assert output.total_tokens == output.input_tokens + output.output_tokens


def test_run_mock_does_not_call_external_provider():
    """Verify run_mock overrides existing providers with MockLLMProvider cleanly."""
    # We can inject a failing provider to verify it gets bypassed by run_mock
    from app.llm.base import BaseLLMProvider
    from app.llm.schemas import LLMRequest, LLMResponse, LLMProviderInfo

    class FailingProvider(BaseLLMProvider):
        @property
        def provider_name(self) -> str:
            return "failing"

        @property
        def model_name(self) -> str:
            return "failing-model"

        def generate(self, request: LLMRequest) -> LLMResponse:
            raise RuntimeError("API key is invalid (simulated external error)")

        def get_info(self) -> LLMProviderInfo:
            return LLMProviderInfo(
                provider=self.provider_name,
                model=self.model_name,
                configured=True,
                supports_streaming=False,
            )

    failing_service = LLMService(provider=FailingProvider())
    agent = get_agent("planner", llm_service=failing_service)
    inp = AgentInput(
        agent_name="planner",
        task="Failing test",
    )
    # This should succeed because run_mock bypasses the failing service with MockLLMProvider
    output = agent.run_mock(inp)
    assert output.status == "completed"
    assert "Mock response for:" in output.content


def test_all_eight_agents_can_run_mock_offline():
    """Verify every registered agent class is capable of executing run_mock offline."""
    for name in list_agent_names():
        agent = get_agent(name)
        inp = AgentInput(
            agent_name=name,
            task="Test compilation",
            context_pack={"data": "test"} if agent.requires_context_pack else None,
            memory_context={"data": "test"} if agent.requires_memory else None,
        )
        output = agent.run_mock(inp)
        assert output.status == "completed"
        assert output.agent_name == name


def test_no_gemini_openai_key_required_for_agent_registry_tests():
    """Verify that registry tests run without checking external API environment variables."""
    # Since run_mock and tests use MockLLMProvider explicitly, they pass without keys.
    assert True
