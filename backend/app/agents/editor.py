"""
AIuthor Backend — Editor Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class EditorAgent(BaseAgent):
    """
    Agent responsible for structural edits, grammar, readability, and consistency transitions.
    """
    agent_name = "editor"
    display_name = "Editor Agent"
    description = "Improves structure, clarity, flow, and consistency."
    requires_context_pack = False
    requires_memory = False
