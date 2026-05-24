"""
AIuthor Backend — Agent Execution Service (Module 7.0B).
"""
from __future__ import annotations

from sqlalchemy.orm import Session
from app.services.llm_service import LLMService
from app.agents.schemas import (
    AgentInput,
    AgentOutput,
    AgentInfo,
    AgentPromptRenderRequest,
    AgentPromptRenderResponse,
)
from app.agents.prompt_registry import PromptRegistry


class AgentExecutionService:
    """
    Service coordinating the invocation, mocking, and prompt compilation of the pipeline agents.
    """

    def __init__(
        self,
        db: Session | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.prompt_registry = PromptRegistry()

    def list_agents(self) -> list[AgentInfo]:
        """
        List details of all supported agents in the system.
        """
        from app.agents.registry import list_agent_info
        return list_agent_info()

    def get_agent_info(self, agent_name: str) -> AgentInfo:
        """
        Fetch capabilities and template prompts for a specific agent name.
        """
        from app.agents.registry import get_agent
        agent = get_agent(agent_name, llm_service=self.llm_service)
        return agent.get_info()

    def render_agent_prompt(
        self,
        request: AgentPromptRenderRequest,
    ) -> AgentPromptRenderResponse:
        """
        Render templates locally for an agent task without executing any LLM provider.
        """
        system_prompt, user_prompt = self.prompt_registry.render_prompt(
            agent_name=request.agent_name,
            task=request.task,
            context=request.context,
            metadata=request.metadata,
        )
        version = self.prompt_registry.get_version(request.agent_name)
        return AgentPromptRenderResponse(
            agent_name=request.agent_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_template=system_prompt,
            version=version,
            metadata=request.metadata,
        )



    def run_agent_once(self, input: AgentInput) -> AgentOutput:
        """
        Run the agent using the configured LLM provider through LLMService.
        Can make external Gemini/OpenAI calls depending on settings and credentials.
        """
        from app.agents.registry import get_agent
        agent = get_agent(input.agent_name, llm_service=self.llm_service)
        output = agent.run(input)

        # Attach real execution metadata
        meta = dict(output.metadata) if output.metadata else {}
        meta["execution_mode"] = "real_dev"
        meta["provider"] = self.llm_service.provider.provider_name
        meta["model"] = self.llm_service.provider.model_name
        meta["warning"] = "Manual dev-only single-agent execution. Not full workflow."
        return output.model_copy(update={"metadata": meta})
