"""Web search tool for searching the internet."""

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from agent_rag.tools.interface import Tool, ToolResponse
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WebSearchConfig:
    """Configuration for web search tool."""
    api_key: Optional[str] = None
    provider: str = "tavily"  # tavily, serper, etc.
    max_results: int = 5


@dataclass
class WebSearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "score": self.score,
        }


class WebSearchTool(Tool[WebSearchConfig]):
    """Tool for searching the public internet."""

    NAME = "web_search"
    DESCRIPTION = """Search the public internet for information.
Use this for current events, public documentation, general knowledge,
or when internal documents don't have the answer."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "tavily",
        max_results: int = 5,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id)
        self.api_key = api_key
        self.provider = provider
        self.max_results = max_results

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    def tool_definition(self) -> dict[str, Any]:
        """Get tool definition."""
        return self.build_tool_definition(
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                },
            },
            required=["query"],
        )

    def run(
        self,
        override_kwargs: Optional[WebSearchConfig] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Execute web search."""
        query = llm_kwargs.get("query", "")
        max_results = llm_kwargs.get("max_results", self.max_results)

        if not query:
            return ToolResponse(llm_response="Error: No query provided")

        # Use override config if provided
        config = override_kwargs
        api_key = config.api_key if config else self.api_key
        provider = config.provider if config else self.provider

        if not api_key:
            return ToolResponse(
                llm_response="Error: Web search API key not configured"
            )

        try:
            if provider == "tavily":
                results = self._search_tavily(query, api_key, max_results)
            else:
                return ToolResponse(
                    llm_response=f"Error: Unknown provider {provider}"
                )

            if not results:
                return ToolResponse(
                    llm_response=f"No web results found for: {query}",
                    rich_response={"results": []},
                )

            # Build response
            response_parts = [f"Web search results for: {query}\n"]

            for i, result in enumerate(results, 1):
                response_parts.append(
                    f"\n[{i}] **{result.title}**\n"
                    f"URL: {result.url}\n"
                    f"{result.snippet}\n"
                )

            return ToolResponse(
                llm_response="\n".join(response_parts),
                rich_response={"results": [r.to_dict() for r in results]},
            )

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResponse(
                llm_response=f"Error performing web search: {str(e)}"
            )

    def _search_tavily(
        self,
        query: str,
        api_key: str,
        max_results: int,
    ) -> list[WebSearchResult]:
        """Search using Tavily API."""
        url = "https://api.tavily.com/search"

        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }

        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", []):
            results.append(WebSearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                score=item.get("score", 0.0),
            ))

        return results
