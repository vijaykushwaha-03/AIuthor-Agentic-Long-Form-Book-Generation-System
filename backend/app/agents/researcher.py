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

    def run(self, input: AgentInput) -> AgentOutput:
        """
        Overrides run to inject external Web Search results into the context pack
        before calling the LLM.
        """
        from app.services.web_search_service import WebSearchService
        import logging
        logger = logging.getLogger(__name__)

        # Extract search query from task (fallback to full task if too long)
        query = input.task if len(input.task) < 100 else input.task[:100]
        
        search_service = WebSearchService()
        if search_service.enabled:
            logger.info("ResearcherAgent executing web search for topic context.")
            results = search_service.search(query, max_results=3)
            formatted_results = search_service.format_search_results(query, results)
            
            # Inject findings into context pack
            if input.context_pack:
                input.context_pack += f"\n\n{formatted_results}"
            else:
                input.context_pack = formatted_results
        
        # Proceed with base agent execution
        return super().run(input)
