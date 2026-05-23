"""
AIuthor Backend — FactChecker Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class FactCheckerAgent(BaseAgent):
    """
    Agent responsible for verifying assertions against reference source documents and context packs.
    """
    agent_name = "fact_checker"
    display_name = "FactChecker Agent"
    description = "Checks claims against citations and flags unsupported statements."
    requires_context_pack = True
    requires_memory = False
