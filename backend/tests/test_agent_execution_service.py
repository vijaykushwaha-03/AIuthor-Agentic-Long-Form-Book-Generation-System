"""
AIuthor Backend Tests — Agent Execution Service Verification (Module 7.0B).
"""
from __future__ import annotations

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.services.agent_execution_service import AgentExecutionService
from app.agents.schemas import AgentInput, AgentInfo, AgentOutput, AgentPromptRenderRequest
from app.agents.exceptions import AgentNotFoundError, AgentPromptError, AgentExecutionError
from app.services.llm_service import LLMService


def test_list_agents_returns_eight_agents(db: Session):
    """Verify list_agents returns exactly the 8 core agents."""
    svc = AgentExecutionService(db=db)
    agents = svc.list_agents()
    assert len(agents) == 8
    names = [a.agent_name for a in agents]
    expected = [
        "planner",
        "researcher",
        "writer",
        "humanizer",
        "editor",
        "fact_checker",
        "memory_keeper",
        "assembler",
    ]
    for name in expected:
        assert name in names


def test_get_agent_info_returns_planner_info(db: Session):
    """Verify get_agent_info returns core metadata for the planner agent."""
    svc = AgentExecutionService(db=db)
    info = svc.get_agent_info("planner")
    assert isinstance(info, AgentInfo)
    assert info.agent_name == "planner"
    assert info.display_name == "Planner Agent"
    assert "Planner" in info.prompt_template
    assert info.version == "v1"


def test_get_agent_info_invalid_raises_agent_not_found(db: Session):
    """Verify get_agent_info raises AgentNotFoundError on invalid agent name."""
    svc = AgentExecutionService(db=db)
    with pytest.raises(AgentNotFoundError):
        svc.get_agent_info("invalid_agent_name")


def test_render_agent_prompt_returns_prompts(db: Session):
    """Verify render_agent_prompt renders system and user prompts correctly."""
    svc = AgentExecutionService(db=db)
    req = AgentPromptRenderRequest(
        agent_name="planner",
        task="Create an outline of a fantasy novel.",
        context={"target_chapters": 10},
        metadata={"user_id": "test-user"},
    )
    res = svc.render_agent_prompt(req)
    assert res.agent_name == "planner"
    assert "Planner" in res.system_prompt
    assert "Create an outline of a fantasy novel." in res.user_prompt
    assert '"target_chapters": 10' in res.user_prompt
    assert '"user_id": "test-user"' in res.user_prompt
    assert res.version == "v1"


def test_render_agent_prompt_includes_task(db: Session):
    """Verify that the rendered prompt includes the user's task string."""
    svc = AgentExecutionService(db=db)
    req = AgentPromptRenderRequest(
        agent_name="researcher",
        task="Verify population details of Atlantis.",
    )
    res = svc.render_agent_prompt(req)
    assert "Verify population details of Atlantis." in res.user_prompt


def test_render_agent_prompt_does_not_call_llm(db: Session, monkeypatch):
    """Verify render_agent_prompt is offline and does not call any LLM Service."""
    svc = AgentExecutionService(db=db)

    def mock_generate(*args, **kwargs):
        raise RuntimeError("Should not be called")

    monkeypatch.setattr(svc.llm_service, "generate_text", mock_generate)

    req = AgentPromptRenderRequest(
        agent_name="writer",
        task="Write chapter 1.",
    )
    # This should complete without exception because no LLM call is made
    res = svc.render_agent_prompt(req)
    assert res.agent_name == "writer"


def test_run_agent_mock_returns_agent_output(db: Session):
    """Verify run_agent_mock returns structured AgentOutput with mock execution mode."""
    svc = AgentExecutionService(db=db)
    inp = AgentInput(
        agent_name="planner",
        task="Plan a book about coding guidelines.",
    )
    output = svc.run_agent_mock(inp)
    assert isinstance(output, AgentOutput)
    assert output.agent_name == "planner"
    assert output.status == "completed"
    assert output.metadata is not None
    assert output.metadata.get("execution_mode") == "mock"


def test_run_agent_mock_planner_works(db: Session):
    """Verify mock execution works for the planner agent specifically."""
    svc = AgentExecutionService(db=db)
    inp = AgentInput(
        agent_name="planner",
        task="Develop outline.",
    )
    output = svc.run_agent_mock(inp)
    assert output.status == "completed"
    assert "Mock response for" in output.content


def test_run_agent_mock_writer_works(db: Session):
    """Verify mock execution works for the writer agent specifically."""
    svc = AgentExecutionService(db=db)
    inp = AgentInput(
        agent_name="writer",
        task="Draft chapter.",
        context_pack={"notes": "test notes"},
        memory_context={"past_chapters": []},
    )
    output = svc.run_agent_mock(inp)
    assert output.status == "completed"
    assert "Mock response for" in output.content


def test_run_agent_mock_invalid_agent_raises_not_found(db: Session):
    """Verify run_agent_mock raises AgentNotFoundError for unregistered agents."""
    svc = AgentExecutionService(db=db)
    inp = AgentInput(
        agent_name="unsupported_agent",
        task="Perform action",
    )
    with pytest.raises(AgentNotFoundError):
        svc.run_agent_mock(inp)


def test_run_agent_mock_does_not_call_gemini_openai(db: Session, monkeypatch):
    """Verify run_agent_mock strictly uses offline provider and doesn't call OpenAI/Gemini."""
    svc = AgentExecutionService(db=db)

    # Inject a failing default provider
    from app.llm.base import BaseLLMProvider
    from app.llm.schemas import LLMRequest, LLMResponse, LLMProviderInfo

    class CrashingLLMProvider(BaseLLMProvider):
        @property
        def provider_name(self) -> str:
            return "crashing"

        @property
        def model_name(self) -> str:
            return "crashing-model"

        def generate(self, request: LLMRequest) -> LLMResponse:
            raise RuntimeError("Tried to call external provider")

        def get_info(self) -> LLMProviderInfo:
            return LLMProviderInfo(
                provider=self.provider_name,
                model=self.model_name,
                configured=True,
                supports_streaming=False,
            )

    svc.llm_service = LLMService(provider=CrashingLLMProvider())

    inp = AgentInput(
        agent_name="humanizer",
        task="Polish tone.",
    )
    # Should succeed because run_agent_mock enforces MockLLMProvider
    output = svc.run_agent_mock(inp)
    assert output.status == "completed"
    assert output.metadata.get("execution_mode") == "mock"


def test_run_agent_once_exists_and_signature_matches(db: Session):
    """Verify run_agent_once method exists and is syntactically ready."""
    svc = AgentExecutionService(db=db)
    assert hasattr(svc, "run_agent_once")
    # We do not execute it in unit tests because it requires real keys, but we check signature
    import inspect
    sig = inspect.signature(svc.run_agent_once)
    assert "input" in sig.parameters
