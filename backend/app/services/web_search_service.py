"""
AIuthor Backend — Web Search Service (Module 7.0A).
Provides external search capabilities for the Researcher agent.
"""
from __future__ import annotations

import logging
from typing import Any

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Service wrapper for web search providers (DuckDuckGo by default).
    Allows agents to retrieve external facts and citations.
    """

    def __init__(self) -> None:
        if DDGS is None:
            logger.warning("duckduckgo_search is not installed. Web search will be disabled.")
        self.enabled = DDGS is not None

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """
        Execute a text search query and return a list of results.
        Returns: [{"title": "...", "href": "...", "body": "..."}, ...]
        """
        if not self.enabled:
            return []
            
        logger.info(f"WebSearchService performing search for: '{query}'")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results
        except Exception as exc:
            logger.error(f"WebSearchService query '{query}' failed: {exc}")
            return []

    def format_search_results(self, query: str, results: list[dict[str, Any]]) -> str:
        """
        Formats search results into a readable string block for prompt injection.
        """
        if not results:
            return f"[Web Search: No external results found for query: '{query}']"
            
        formatted = f"[External Web Search Results for query: '{query}']\n"
        for i, r in enumerate(results, start=1):
            title = r.get('title', 'Unknown Title')
            href = r.get('href', 'Unknown URL')
            body = r.get('body', 'No content summary available.')
            formatted += f"Result {i}:\nTitle: {title}\nURL: {href}\nSnippet: {body}\n\n"
        return formatted.strip()
