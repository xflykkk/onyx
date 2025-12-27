"""Think tool for Deep Research agent.

Allows the agent to reason about search results and generate refined queries.
"""

from dataclasses import dataclass
from typing import Any, Optional

from agent_rag.core.models import Chunk
from agent_rag.llm.interface import LLM, LLMMessage
from agent_rag.tools.interface import Tool, ToolResponse
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


THINK_SYSTEM_PROMPT = """You are a research analyst helping to analyze search results and plan next steps.

Your task is to:
1. Analyze the provided search results
2. Identify what information is still missing or unclear
3. Generate refined search queries to fill knowledge gaps
4. Determine if you have enough information to answer the question

Be thorough and systematic in your analysis."""


@dataclass
class ThinkToolConfig:
    """Configuration for Think tool."""
    max_queries: int = 3
    include_reasoning: bool = True


@dataclass
class ThinkResult:
    """Result of think tool execution."""
    analysis: str
    refined_queries: list[str]
    knowledge_gaps: list[str]
    has_sufficient_info: bool
    confidence: float
    reasoning: Optional[str] = None


class ThinkTool(Tool[ThinkToolConfig]):
    """
    Think tool for analyzing search results and generating refined queries.

    Used by Deep Research agents to:
    - Analyze current search results
    - Identify knowledge gaps
    - Generate focused follow-up queries
    - Decide when enough information has been gathered
    """

    NAME = "think"
    DESCRIPTION = """Analyze search results and plan next research steps.
Use this to reflect on current findings, identify gaps, and generate refined queries."""

    def __init__(
        self,
        llm: LLM,
        max_queries: int = 3,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id)
        self.llm = llm
        self.max_queries = max_queries

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
                "question": {
                    "type": "string",
                    "description": "The original research question",
                },
                "current_findings": {
                    "type": "string",
                    "description": "Summary of current search findings",
                },
                "search_history": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of queries already searched",
                },
            },
            required=["question", "current_findings"],
        )

    def run(
        self,
        override_kwargs: Optional[ThinkToolConfig] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Execute think tool."""
        question = llm_kwargs.get("question", "")
        current_findings = llm_kwargs.get("current_findings", "")
        search_history = llm_kwargs.get("search_history", [])

        config = override_kwargs or ThinkToolConfig()

        result = self.think(
            question=question,
            current_findings=current_findings,
            search_history=search_history,
            max_queries=config.max_queries,
        )

        response_text = self._format_response(result)

        return ToolResponse(
            llm_response=response_text,
            rich_response={
                "result": result,
                "refined_queries": result.refined_queries,
                "has_sufficient_info": result.has_sufficient_info,
            },
        )

    def think(
        self,
        question: str,
        current_findings: str,
        search_history: Optional[list[str]] = None,
        max_queries: int = 3,
    ) -> ThinkResult:
        """
        Analyze findings and generate refined queries.

        Args:
            question: Original research question
            current_findings: Summary of what has been found
            search_history: Previous search queries
            max_queries: Maximum number of refined queries to generate

        Returns:
            ThinkResult with analysis and next steps
        """
        search_history = search_history or []

        prompt = self._build_prompt(
            question=question,
            current_findings=current_findings,
            search_history=search_history,
            max_queries=max_queries,
        )

        messages = [
            LLMMessage(role="system", content=THINK_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]

        response = self.llm.generate(messages)

        return self._parse_response(response.content)

    def _build_prompt(
        self,
        question: str,
        current_findings: str,
        search_history: list[str],
        max_queries: int,
    ) -> str:
        """Build prompt for think analysis."""
        history_text = "\n".join(f"- {q}" for q in search_history) if search_history else "None yet"

        return f"""## Research Question
{question}

## Current Findings
{current_findings}

## Previous Searches
{history_text}

## Your Task
Analyze the current findings and determine next steps.

Please respond in the following format:

### Analysis
[Your analysis of the current findings]

### Knowledge Gaps
- [Gap 1]
- [Gap 2]
- ...

### Refined Queries
[Generate up to {max_queries} focused search queries to fill the gaps]
1. [Query 1]
2. [Query 2]
...

### Sufficient Information
[YES/NO] - Do we have enough information to comprehensively answer the question?

### Confidence
[0.0-1.0] - How confident are you in the current findings?

### Reasoning
[Brief explanation of your assessment]"""

    def _parse_response(self, response: str) -> ThinkResult:
        """Parse LLM response into ThinkResult."""
        # Extract sections
        analysis = self._extract_section(response, "Analysis")
        gaps = self._extract_list(response, "Knowledge Gaps")
        queries = self._extract_numbered_list(response, "Refined Queries")
        sufficient = self._extract_section(response, "Sufficient Information")
        confidence_text = self._extract_section(response, "Confidence")
        reasoning = self._extract_section(response, "Reasoning")

        # Parse boolean
        has_sufficient = "yes" in sufficient.lower() if sufficient else False

        # Parse confidence
        try:
            confidence = float(confidence_text.strip()) if confidence_text else 0.5
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.5

        return ThinkResult(
            analysis=analysis or "No analysis provided",
            refined_queries=queries[:self.max_queries],
            knowledge_gaps=gaps,
            has_sufficient_info=has_sufficient,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _extract_section(self, text: str, header: str) -> str:
        """Extract content under a header."""
        import re
        pattern = rf"###?\s*{header}\s*\n(.*?)(?=###|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_list(self, text: str, header: str) -> list[str]:
        """Extract bullet list items under a header."""
        section = self._extract_section(text, header)
        items = []
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                items.append(line[2:].strip())
            elif line.startswith('* '):
                items.append(line[2:].strip())
        return items

    def _extract_numbered_list(self, text: str, header: str) -> list[str]:
        """Extract numbered list items under a header."""
        import re
        section = self._extract_section(text, header)
        items = []
        for line in section.split('\n'):
            line = line.strip()
            # Match patterns like "1. ", "1) ", "1: "
            match = re.match(r'^\d+[\.\)\:]\s*(.+)$', line)
            if match:
                items.append(match.group(1).strip())
        return items

    def _format_response(self, result: ThinkResult) -> str:
        """Format result for LLM response."""
        parts = [
            "## Analysis",
            result.analysis,
            "",
        ]

        if result.knowledge_gaps:
            parts.append("## Knowledge Gaps")
            for gap in result.knowledge_gaps:
                parts.append(f"- {gap}")
            parts.append("")

        if result.refined_queries:
            parts.append("## Suggested Next Queries")
            for i, query in enumerate(result.refined_queries, 1):
                parts.append(f"{i}. {query}")
            parts.append("")

        status = "Yes" if result.has_sufficient_info else "No"
        parts.append(f"## Sufficient Information: {status}")
        parts.append(f"Confidence: {result.confidence:.1%}")

        if result.reasoning:
            parts.append("")
            parts.append(f"## Reasoning")
            parts.append(result.reasoning)

        return "\n".join(parts)


def create_think_tool(llm: LLM, max_queries: int = 3) -> ThinkTool:
    """Factory function to create a ThinkTool."""
    return ThinkTool(llm=llm, max_queries=max_queries)
