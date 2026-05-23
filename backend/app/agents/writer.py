"""
AIuthor Backend — Writer Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class WriterAgent(BaseAgent):
    """
    Agent responsible for writing structured chapter prose using resources and context.
    """
    agent_name = "writer"
    display_name = "Writer Agent"
    description = "Writes long-form chapter drafts using plan, context, memory, tone, and citations."
    requires_context_pack = True
    requires_memory = True
