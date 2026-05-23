"""
AIuthor Backend — Humanizer Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class HumanizerAgent(BaseAgent):
    """
    Agent responsible for polishing rhythm, voice, style, and natural flow of the prose.
    """
    agent_name = "humanizer"
    display_name = "Humanizer Agent"
    description = "Improves naturalness and style while preserving facts and citations."
    requires_context_pack = False
    requires_memory = True
