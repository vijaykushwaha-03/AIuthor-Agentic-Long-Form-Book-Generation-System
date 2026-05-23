"""
AIuthor Backend — Assembler Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class AssemblerAgent(BaseAgent):
    """
    Agent responsible for compiling chapters and structuring final manuscript deliverables.
    """
    agent_name = "assembler"
    display_name = "Assembler Agent"
    description = "Prepares final book structure and export readiness."
    requires_context_pack = False
    requires_memory = False
