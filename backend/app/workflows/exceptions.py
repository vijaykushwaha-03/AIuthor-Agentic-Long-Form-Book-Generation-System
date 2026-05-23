"""
AIuthor Backend — Workflow Custom Exceptions (Module 7.1A).
"""
from __future__ import annotations


class WorkflowError(Exception):
    """
    Base class for all workflow-related exceptions in the system.
    """
    def __init__(
        self,
        message: str,
        workflow_name: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.workflow_name = workflow_name
        self.details = details or {}


class WorkflowConfigurationError(WorkflowError, ValueError):
    """
    Exception raised for invalid or unsupported workflow configuration options.
    """
    pass


class WorkflowExecutionError(WorkflowError):
    """
    Exception raised when a workflow node or graph execution fails at runtime.
    """
    pass
