"""Report generator for Deep Research.

Synthesizes findings from multiple research agents into a cohesive report.
"""

from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from agent_rag.agent.deep_research.research_agent import ResearchFindings
from agent_rag.citation.processor import DynamicCitationProcessor
from agent_rag.citation.utils import chunks_to_citations, format_citation_list
from agent_rag.core.models import Chunk, Citation
from agent_rag.llm.interface import LLM, LLMMessage
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


REPORT_SYSTEM_PROMPT = """You are a research report writer synthesizing findings from multiple research agents.

Your task is to:
1. Integrate findings from all research agents into a cohesive report
2. Identify common themes and contradictions
3. Cite sources using [N] notation where N corresponds to the source number
4. Provide a clear, well-structured answer to the research question
5. Note any limitations or areas requiring further research

Write in a professional, objective tone. Be thorough but concise."""


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    include_methodology: bool = True
    include_limitations: bool = True
    max_length: int = 4000
    citation_style: str = "numbered"


@dataclass
class ResearchReport:
    """Generated research report."""
    title: str
    summary: str
    full_report: str
    citations: list[Citation]
    key_findings: list[str]
    limitations: list[str]
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """
    Generate comprehensive research reports from research findings.

    Takes findings from multiple research agents and synthesizes them
    into a cohesive, well-cited report.
    """

    def __init__(
        self,
        llm: LLM,
        config: Optional[ReportConfig] = None,
    ) -> None:
        """
        Initialize report generator.

        Args:
            llm: LLM provider
            config: Report configuration
        """
        self.llm = llm
        self.config = config or ReportConfig()

    def generate(
        self,
        question: str,
        findings: list[ResearchFindings],
        context: Optional[dict[str, Any]] = None,
    ) -> ResearchReport:
        """
        Generate a research report.

        Args:
            question: Original research question
            findings: Findings from research agents
            context: Optional additional context

        Returns:
            ResearchReport with synthesized content
        """
        # Collect all sources
        all_chunks = self._collect_sources(findings)
        citations = chunks_to_citations(all_chunks)

        # Build prompt
        prompt = self._build_prompt(question, findings, citations)

        messages = [
            LLMMessage(role="system", content=REPORT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]

        response = self.llm.generate(messages)

        # Process citations in response
        processor = DynamicCitationProcessor(all_chunks)
        processed_content = processor.process_complete_text(response.content)
        final_citations = processor.get_citations()

        # Extract structured content
        return self._parse_report(
            question=question,
            content=processed_content,
            citations=final_citations,
            findings=findings,
        )

    def generate_stream(
        self,
        question: str,
        findings: list[ResearchFindings],
        context: Optional[dict[str, Any]] = None,
    ) -> Iterator[tuple[str, Optional[ResearchReport]]]:
        """
        Generate report with streaming.

        Args:
            question: Original research question
            findings: Findings from research agents
            context: Optional additional context

        Yields:
            Tuples of (token, final_report) where report is None until complete
        """
        all_chunks = self._collect_sources(findings)
        citations = chunks_to_citations(all_chunks)

        prompt = self._build_prompt(question, findings, citations)

        messages = [
            LLMMessage(role="system", content=REPORT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]

        processor = DynamicCitationProcessor(all_chunks)
        full_content = ""

        for chunk in self.llm.generate_stream(messages):
            if chunk.content:
                # Process token through citation processor
                processed = processor.process_token(chunk.content)
                full_content += chunk.content
                if processed:
                    yield (processed, None)

        # Flush remaining content
        remaining = processor.flush()
        if remaining:
            yield (remaining, None)

        # Get final citations
        final_citations = processor.get_citations()

        # Parse and yield final report
        processed_content = processor.process_complete_text(full_content)
        report = self._parse_report(
            question=question,
            content=processed_content,
            citations=final_citations,
            findings=findings,
        )
        yield ("", report)

    def _collect_sources(self, findings: list[ResearchFindings]) -> list[Chunk]:
        """Collect and deduplicate sources from all findings."""
        seen_ids: set[str] = set()
        chunks: list[Chunk] = []

        for finding in findings:
            for chunk in finding.sources:
                if chunk.unique_id not in seen_ids:
                    seen_ids.add(chunk.unique_id)
                    chunks.append(chunk)

        return chunks

    def _build_prompt(
        self,
        question: str,
        findings: list[ResearchFindings],
        citations: list[Citation],
    ) -> str:
        """Build prompt for report generation."""
        # Build findings section
        findings_text = []
        for i, finding in enumerate(findings, 1):
            findings_text.append(f"""### Research Agent {i}: {finding.sub_question}

**Summary:** {finding.summary}

**Key Facts:**
{chr(10).join('- ' + fact for fact in finding.key_facts)}

**Confidence:** {finding.confidence:.1%}
**Sources Used:** {len(finding.sources)}
""")

        # Build sources section
        sources_text = []
        for citation in citations:
            source_info = f"[{citation.citation_id}] {citation.title or 'Untitled'}"
            if citation.source_type:
                source_info += f" ({citation.source_type})"
            sources_text.append(source_info)
            if citation.content:
                # Truncate long content
                content = citation.content[:500] + "..." if len(citation.content) > 500 else citation.content
                sources_text.append(f"   Content: {content}")
            sources_text.append("")

        return f"""## Research Question
{question}

## Findings from Research Agents
{chr(10).join(findings_text)}

## Available Sources
{chr(10).join(sources_text)}

## Instructions
Please write a comprehensive research report that:
1. Answers the research question thoroughly
2. Synthesizes findings from all research agents
3. Uses [N] citations to reference sources
4. Includes a brief summary at the start
5. Notes any limitations or areas needing more research

Structure your report with clear sections."""

    def _parse_report(
        self,
        question: str,
        content: str,
        citations: list[Citation],
        findings: list[ResearchFindings],
    ) -> ResearchReport:
        """Parse generated content into structured report."""
        # Extract sections
        summary = self._extract_summary(content)
        key_findings = self._extract_key_findings(content)
        limitations = self._extract_limitations(content)

        # Calculate overall confidence
        if findings:
            avg_confidence = sum(f.confidence for f in findings) / len(findings)
        else:
            avg_confidence = 0.0

        # Generate title
        title = self._generate_title(question)

        return ResearchReport(
            title=title,
            summary=summary,
            full_report=content,
            citations=citations,
            key_findings=key_findings,
            limitations=limitations,
            confidence=avg_confidence,
            metadata={
                "num_sources": len(citations),
                "num_agents": len(findings),
                "total_queries": sum(len(f.search_queries_used) for f in findings),
            },
        )

    def _extract_summary(self, content: str) -> str:
        """Extract summary from report."""
        import re

        # Look for explicit summary section
        match = re.search(
            r'(?:##?\s*(?:Summary|Executive Summary|Overview))\s*\n(.*?)(?=##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Fall back to first paragraph
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith('#') and len(para) > 50:
                return para

        return content[:500] if len(content) > 500 else content

    def _extract_key_findings(self, content: str) -> list[str]:
        """Extract key findings from report."""
        import re

        findings = []

        # Look for findings/conclusions section
        match = re.search(
            r'(?:##?\s*(?:Key Findings|Findings|Conclusions))\s*\n(.*?)(?=##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if match:
            section = match.group(1)
            # Extract bullet points
            for line in section.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    findings.append(line[2:].strip())
                elif re.match(r'^\d+[\.\)]\s+', line):
                    findings.append(re.sub(r'^\d+[\.\)]\s+', '', line).strip())

        return findings[:10]  # Limit to 10 findings

    def _extract_limitations(self, content: str) -> list[str]:
        """Extract limitations from report."""
        import re

        limitations = []

        match = re.search(
            r'(?:##?\s*(?:Limitations|Caveats|Further Research))\s*\n(.*?)(?=##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE,
        )

        if match:
            section = match.group(1)
            for line in section.split('\n'):
                line = line.strip()
                if line.startswith('- ') or line.startswith('* '):
                    limitations.append(line[2:].strip())

        return limitations

    def _generate_title(self, question: str) -> str:
        """Generate report title from question."""
        # Simple title generation - clean up the question
        title = question.strip()

        # Remove question mark if present
        if title.endswith('?'):
            title = title[:-1]

        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]

        # Add "Research Report:" prefix
        return f"Research Report: {title}"


def format_report_markdown(report: ResearchReport) -> str:
    """Format report as markdown."""
    parts = [
        f"# {report.title}",
        "",
        f"**Confidence:** {report.confidence:.1%}",
        "",
        "## Summary",
        report.summary,
        "",
        "---",
        "",
        report.full_report,
        "",
    ]

    if report.key_findings:
        parts.extend([
            "## Key Findings",
            "",
        ])
        for finding in report.key_findings:
            parts.append(f"- {finding}")
        parts.append("")

    if report.limitations:
        parts.extend([
            "## Limitations",
            "",
        ])
        for limitation in report.limitations:
            parts.append(f"- {limitation}")
        parts.append("")

    if report.citations:
        parts.append(format_citation_list(report.citations))

    return "\n".join(parts)
