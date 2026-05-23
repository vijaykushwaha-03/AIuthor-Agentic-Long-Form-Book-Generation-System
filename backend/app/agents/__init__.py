"""
AIuthor Backend — Agents Package.
"""
from __future__ import annotations

from app.agents.schemas import (
    AgentInput,
    AgentOutput,
    AgentInfo,
    AgentPromptRenderRequest,
    AgentPromptRenderResponse,
)
from app.agents.exceptions import (
    AgentError,
    AgentNotFoundError,
    AgentPromptError,
    AgentExecutionError,
)
from app.agents.prompt_registry import PromptRegistry
from app.agents.base import BaseAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.writer import WriterAgent
from app.agents.humanizer import HumanizerAgent
from app.agents.editor import EditorAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.memory_keeper import MemoryKeeperAgent
from app.agents.assembler import AssemblerAgent
from app.agents.registry import (
    list_agent_names,
    list_agent_info,
    get_agent,
)

__all__ = [
    "AgentInput",
    "AgentOutput",
    "AgentInfo",
    "AgentPromptRenderRequest",
    "AgentPromptRenderResponse",
    "AgentError",
    "AgentNotFoundError",
    "AgentPromptError",
    "AgentExecutionError",
    "PromptRegistry",
    "BaseAgent",
    "PlannerAgent",
    "ResearcherAgent",
    "WriterAgent",
    "HumanizerAgent",
    "EditorAgent",
    "FactCheckerAgent",
    "MemoryKeeperAgent",
    "AssemblerAgent",
    "list_agent_names",
    "list_agent_info",
    "get_agent",
]
