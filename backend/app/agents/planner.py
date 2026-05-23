"""
AIuthor Backend — Planner Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Agent responsible for converting the user's topic and settings into a detailed book blueprint.
    """
    agent_name = "planner"
    display_name = "Planner Agent"
    description = "Creates the book outline and chapter plan."
    requires_context_pack = False
    requires_memory = False
