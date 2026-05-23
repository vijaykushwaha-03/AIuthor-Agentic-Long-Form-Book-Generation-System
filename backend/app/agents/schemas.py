"""
AIuthor Backend — Agent Pydantic Schemas (Module 7.0A).
"""
from __future__ import annotations

from uuid import UUID
from pydantic import Field, field_validator
from app.schemas.base import BaseSchema


class AgentInput(BaseSchema):
    """
    Input data model required to invoke any AIuthor agent execution context.
    """
    run_id: UUID | None = None
    book_id: UUID | None = None
    chapter_id: UUID | None = None
    agent_name: str
    task: str = Field(..., min_length=1)
    context_pack: dict | None = None
    memory_context: dict | None = None
    payload: dict | None = None
    metadata: dict | None = None


class AgentOutput(BaseSchema):
    """
    Output data returned upon completion of an agent task execution.
    """
    agent_name: str
    status: str
    content: str | None = None
    structured_output: dict | None = None
    error_message: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict | None = None


class AgentInfo(BaseSchema):
    """
    Metadata representation summarizing agent properties and capabilities.
    """
    agent_name: str
    display_name: str
    description: str
    prompt_template: str
    version: str
    enabled: bool = True
    requires_context_pack: bool = False
    requires_memory: bool = False


class AgentPromptRenderRequest(BaseSchema):
    """
    Request model used to render compile system and user prompts locally.
    """
    agent_name: str
    task: str = Field(..., min_length=1)
    context: dict | None = None
    metadata: dict | None = None


class AgentPromptRenderResponse(BaseSchema):
    """
    Response containing the rendered system and user prompt strings.
    """
    agent_name: str
    system_prompt: str
    user_prompt: str
    prompt_template: str
    version: str
    metadata: dict | None = None
