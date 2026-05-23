"""
AIuthor Backend — Researcher Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class ResearcherAgent(BaseAgent):
    """
    Agent responsible for analyzing source context packs and extracting cited findings.
    """
    agent_name = "researcher"
    display_name = "Researcher Agent"
    description = "Extracts evidence from context packs and preserves citations."
    requires_context_pack = True
    requires_memory = False
