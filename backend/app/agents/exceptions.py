"""
AIuthor Backend — Agent Custom Exceptions (Module 7.0A).
"""
from __future__ import annotations


class AgentError(Exception):
    """
    Base class for all agent-related exceptions in the system.
    """
    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.agent_name = agent_name
        self.details = details or {}


class AgentNotFoundError(AgentError):
    """
    Exception raised when a requested agent name is not found in the registry.
    """
    pass


class AgentPromptError(AgentError):
    """
    Exception raised when template loading, parsing, or rendering fails.
    """
    pass


class AgentExecutionError(AgentError):
    """
    Exception raised when an agent fails during LLM execution or payload parsing.
    """
    pass
