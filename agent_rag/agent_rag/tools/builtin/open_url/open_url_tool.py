"""Open URL tool for fetching web page content."""

from dataclasses import dataclass
from typing import Any, Optional
import re

import httpx

from agent_rag.tools.interface import Tool, ToolResponse
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OpenURLConfig:
    """Configuration for open URL tool."""
    timeout: int = 30
    max_content_length: int = 50000


def extract_text_from_html(html: str) -> str:
    """Simple HTML to text extraction."""
    # Remove script and style elements
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Remove tags
    html = re.sub(r'<[^>]+>', ' ', html)

    # Decode HTML entities
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&amp;', '&')
    html = html.replace('&quot;', '"')

    # Clean up whitespace
    html = re.sub(r'\s+', ' ', html)
    html = html.strip()

    return html


class OpenURLTool(Tool[OpenURLConfig]):
    """Tool for opening and reading web page content."""

    NAME = "open_url"
    DESCRIPTION = """Open a URL and retrieve its content.
Use this to read full content from web pages found via web search,
or to access specific documentation pages."""

    def __init__(
        self,
        timeout: int = 30,
        max_content_length: int = 50000,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id)
        self.timeout = timeout
        self.max_content_length = max_content_length

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
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to open and read",
                },
            },
            required=["urls"],
        )

    def run(
        self,
        override_kwargs: Optional[OpenURLConfig] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Fetch and return content from URLs."""
        urls = llm_kwargs.get("urls", [])

        if not urls:
            return ToolResponse(llm_response="Error: No URLs provided")

        if isinstance(urls, str):
            urls = [urls]

        # Use override config if provided
        config = override_kwargs
        timeout = config.timeout if config else self.timeout
        max_length = config.max_content_length if config else self.max_content_length

        results = []
        response_parts = []

        for url in urls[:5]:  # Limit to 5 URLs
            try:
                content = self._fetch_url(url, timeout, max_length)
                results.append({
                    "url": url,
                    "content": content,
                    "success": True,
                })
                response_parts.append(f"\n## Content from {url}\n\n{content}\n")

            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                results.append({
                    "url": url,
                    "error": str(e),
                    "success": False,
                })
                response_parts.append(f"\n## Error fetching {url}\n\n{str(e)}\n")

        return ToolResponse(
            llm_response="\n".join(response_parts),
            rich_response={"results": results},
        )

    def _fetch_url(
        self,
        url: str,
        timeout: int,
        max_length: int,
    ) -> str:
        """Fetch content from a URL."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AgentRAG/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                html = response.text
                text = extract_text_from_html(html)
            elif "text/plain" in content_type or "application/json" in content_type:
                text = response.text
            else:
                text = f"[Binary content of type: {content_type}]"

            # Truncate if too long
            if len(text) > max_length:
                text = text[:max_length] + f"\n\n[Content truncated at {max_length} characters]"

            return text
