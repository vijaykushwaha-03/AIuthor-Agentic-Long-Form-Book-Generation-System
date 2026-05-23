"""
AIuthor Backend — Agent Registry (Module 7.0A).
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from app.services.llm_service import LLMService
from app.agents.exceptions import AgentNotFoundError

from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.writer import WriterAgent
from app.agents.humanizer import HumanizerAgent
from app.agents.editor import EditorAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.memory_keeper import MemoryKeeperAgent
from app.agents.assembler import AssemblerAgent

if TYPE_CHECKING:
    from app.agents.base import BaseAgent
    from app.agents.schemas import AgentInfo

SUPPORTED_AGENTS = {
    "planner": PlannerAgent,
    "researcher": ResearcherAgent,
    "writer": WriterAgent,
    "humanizer": HumanizerAgent,
    "editor": EditorAgent,
    "fact_checker": FactCheckerAgent,
    "memory_keeper": MemoryKeeperAgent,
    "assembler": AssemblerAgent,
}


def list_agent_names() -> list[str]:
    """
    Return list of names of all registered agents in the system.
    """
    return list(SUPPORTED_AGENTS.keys())


def list_agent_info() -> list[AgentInfo]:
    """
    Instantiate each agent using a default environment context and compile metadata descriptors.
    """
    # Create a single LLMService and PromptRegistry to share across temporary instantiation
    from app.agents.prompt_registry import PromptRegistry
    llm_svc = LLMService()
    registry = PromptRegistry()
    
    info_list = []
    for name in list_agent_names():
        agent_cls = SUPPORTED_AGENTS[name]
        agent_instance = agent_cls(llm_service=llm_svc, prompt_registry=registry)
        info_list.append(agent_instance.get_info())
    return info_list


def get_agent(agent_name: str, llm_service: LLMService | None = None) -> BaseAgent:
    """
    Lookup and return an instance of the specified agent.
    Raises AgentNotFoundError if the agent name is unsupported.
    """
    if agent_name not in SUPPORTED_AGENTS:
        raise AgentNotFoundError(
            message=f"Agent '{agent_name}' is not registered in the system.",
            agent_name=agent_name,
        )
    
    agent_cls = SUPPORTED_AGENTS[agent_name]
    return agent_cls(llm_service=llm_service)
