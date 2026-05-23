"""
AIuthor Backend — MemoryKeeper Agent (Module 7.0A).
"""
from __future__ import annotations

from app.agents.base import BaseAgent


class MemoryKeeperAgent(BaseAgent):
    """
    Agent responsible for extracting narrative elements and logging them for consistency.
    """
    agent_name = "memory_keeper"
    display_name = "MemoryKeeper Agent"
    description = "Extracts stable memory records for long-book continuity."
    requires_context_pack = False
    requires_memory = True
