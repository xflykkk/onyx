"""Research agent for Deep Research.

Individual research agents that work in parallel to explore different aspects
of a research question.
"""

from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from agent_rag.agent.step import AgentStep
from agent_rag.core.models import Chunk, Message, ToolCall
from agent_rag.llm.interface import LLM
from agent_rag.tools.registry import ToolRegistry
from agent_rag.tools.runner import ToolRunner
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


RESEARCH_AGENT_PROMPT = """You are a focused research agent investigating a specific aspect of a research question.

Your role:
1. Use the search tool to find relevant information
2. Analyze and summarize your findings
3. Identify any gaps that need further investigation
4. Be thorough but focused on your assigned sub-question

When you have gathered sufficient information, provide a clear summary of your findings."""


@dataclass
class ResearchAgentConfig:
    """Configuration for research agent."""
    max_cycles: int = 3
    max_search_results: int = 10


@dataclass
class ResearchFindings:
    """Findings from a research agent."""
    sub_question: str
    summary: str
    key_facts: list[str]
    sources: list[Chunk]
    confidence: float
    search_queries_used: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchAgent:
    """
    Individual research agent for exploring a specific sub-question.

    Part of the Deep Research system where multiple research agents
    work in parallel, each focusing on different aspects of the main question.
    """

    def __init__(
        self,
        llm: LLM,
        tool_registry: ToolRegistry,
        config: Optional[ResearchAgentConfig] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        Initialize research agent.

        Args:
            llm: LLM provider
            tool_registry: Registry of available tools
            config: Agent configuration
            agent_id: Unique identifier for this agent
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.config = config or ResearchAgentConfig()
        self.agent_id = agent_id or "research_agent"

        self.tool_runner = ToolRunner(tool_registry)
        self.step_executor = AgentStep(
            llm=llm,
            tool_registry=tool_registry,
            tool_runner=self.tool_runner,
        )

        # State
        self.messages: list[Message] = []
        self.retrieved_chunks: list[Chunk] = []
        self.search_queries: list[str] = []
        self.cycle_count: int = 0

    def reset(self) -> None:
        """Reset agent state."""
        self.messages = []
        self.retrieved_chunks = []
        self.search_queries = []
        self.cycle_count = 0

    def research(
        self,
        sub_question: str,
        main_question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ResearchFindings:
        """
        Research a specific sub-question.

        Args:
            sub_question: Specific aspect to research
            main_question: Original main question for context
            context: Optional context for tools

        Returns:
            ResearchFindings with summary and sources
        """
        self.reset()

        # Initialize conversation
        system_prompt = f"""{RESEARCH_AGENT_PROMPT}

Main Research Question: {main_question}
Your Focus: {sub_question}"""

        self.messages.append(Message(role="system", content=system_prompt))
        self.messages.append(Message(
            role="user",
            content=f"Please research: {sub_question}",
        ))

        # Run research cycles
        while self.cycle_count < self.config.max_cycles:
            self.cycle_count += 1

            step_result = self.step_executor.execute(
                messages=self.messages,
                tools=self.tool_registry.get_all_definitions(),
            )

            # Add assistant response
            if step_result.content or step_result.tool_calls:
                self.messages.append(Message(
                    role="assistant",
                    content=step_result.content,
                    tool_calls=step_result.tool_calls if step_result.tool_calls else None,
                ))

            # Execute tools
            if step_result.tool_calls:
                tool_results = self.step_executor.execute_tools(
                    step_result.tool_calls,
                    context=context,
                )

                for tool_call, result in tool_results:
                    self.messages.append(Message(
                        role="tool",
                        content=result,
                        tool_call_id=tool_call.id,
                    ))

                    # Track search queries
                    if tool_call.name in ["internal_search", "web_search"]:
                        args = tool_call.parsed_arguments
                        if "query" in args:
                            self.search_queries.append(args["query"])

                    # Extract chunks from results
                    self._extract_chunks_from_result(tool_call, result)

            if not step_result.should_continue:
                break

        # Generate findings
        return self._compile_findings(sub_question)

    def research_stream(
        self,
        sub_question: str,
        main_question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Iterator[tuple[str, Optional[ResearchFindings]]]:
        """
        Research with streaming output.

        Args:
            sub_question: Specific aspect to research
            main_question: Original main question
            context: Optional context for tools

        Yields:
            Tuples of (token, final_findings) where findings is None until complete
        """
        self.reset()

        system_prompt = f"""{RESEARCH_AGENT_PROMPT}

Main Research Question: {main_question}
Your Focus: {sub_question}"""

        self.messages.append(Message(role="system", content=system_prompt))
        self.messages.append(Message(
            role="user",
            content=f"Please research: {sub_question}",
        ))

        while self.cycle_count < self.config.max_cycles:
            self.cycle_count += 1

            accumulated_content = ""
            step_result = None

            for token, result in self.step_executor.execute_stream(
                messages=self.messages,
                tools=self.tool_registry.get_all_definitions(),
            ):
                if token:
                    accumulated_content += token
                    yield (token, None)

                if result:
                    step_result = result

            if step_result is None:
                break

            if accumulated_content or step_result.tool_calls:
                self.messages.append(Message(
                    role="assistant",
                    content=accumulated_content,
                    tool_calls=step_result.tool_calls if step_result.tool_calls else None,
                ))

            if step_result.tool_calls:
                tool_results = self.step_executor.execute_tools(
                    step_result.tool_calls,
                    context=context,
                )

                for tool_call, result in tool_results:
                    self.messages.append(Message(
                        role="tool",
                        content=result,
                        tool_call_id=tool_call.id,
                    ))

                    if tool_call.name in ["internal_search", "web_search"]:
                        args = tool_call.parsed_arguments
                        if "query" in args:
                            self.search_queries.append(args["query"])

                    self._extract_chunks_from_result(tool_call, result)

            if not step_result.should_continue:
                break

        findings = self._compile_findings(sub_question)
        yield ("", findings)

    def _extract_chunks_from_result(
        self,
        tool_call: ToolCall,
        result: str,
    ) -> None:
        """Extract chunks from tool result if available."""
        # In a real implementation, this would parse structured tool results
        # For now, we track that a search was performed
        if hasattr(self.tool_runner, 'last_result'):
            last_result = self.tool_runner.last_result
            if last_result and last_result.rich_response:
                chunks = last_result.rich_response.get("chunks", [])
                if isinstance(chunks, list):
                    for chunk in chunks:
                        if isinstance(chunk, Chunk):
                            self.retrieved_chunks.append(chunk)

    def _compile_findings(self, sub_question: str) -> ResearchFindings:
        """Compile research findings from conversation."""
        # Get last assistant message as summary
        summary = ""
        for msg in reversed(self.messages):
            if msg.role == "assistant" and msg.content and not msg.tool_calls:
                summary = msg.content
                break

        # Extract key facts (simplified - would use more sophisticated extraction)
        key_facts = self._extract_key_facts(summary)

        # Calculate confidence based on sources found
        num_sources = len(self.retrieved_chunks)
        confidence = min(1.0, num_sources * 0.15 + 0.3)  # Base 0.3, +0.15 per source

        return ResearchFindings(
            sub_question=sub_question,
            summary=summary or "No findings available",
            key_facts=key_facts,
            sources=self.retrieved_chunks.copy(),
            confidence=confidence,
            search_queries_used=self.search_queries.copy(),
            metadata={
                "cycles": self.cycle_count,
                "agent_id": self.agent_id,
            },
        )

    def _extract_key_facts(self, text: str) -> list[str]:
        """Extract key facts from summary text."""
        # Simple extraction - split by sentences and take key ones
        import re
        sentences = re.split(r'[.!?]\s+', text)

        key_facts = []
        for sentence in sentences[:5]:  # Take up to 5 key facts
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short fragments
                key_facts.append(sentence)

        return key_facts


def run_research_agents_parallel(
    agents: list[ResearchAgent],
    sub_questions: list[str],
    main_question: str,
    context: Optional[dict[str, Any]] = None,
    max_workers: int = 3,
) -> list[ResearchFindings]:
    """
    Run multiple research agents in parallel.

    Args:
        agents: List of research agents
        sub_questions: Sub-questions to research (one per agent)
        main_question: Original main question
        context: Optional context for tools
        max_workers: Maximum parallel workers

    Returns:
        List of ResearchFindings from each agent
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if len(agents) != len(sub_questions):
        raise ValueError("Number of agents must match number of sub-questions")

    results: list[tuple[int, ResearchFindings]] = []

    def run_agent(idx: int) -> tuple[int, ResearchFindings]:
        agent = agents[idx]
        sub_question = sub_questions[idx]
        return (idx, agent.research(sub_question, main_question, context))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_agent, i): i
            for i in range(len(agents))
        }

        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                idx = futures[future]
                logger.error(f"Research agent {idx} failed: {e}")
                # Add empty result for failed agent
                results.append((idx, ResearchFindings(
                    sub_question=sub_questions[idx],
                    summary=f"Research failed: {str(e)}",
                    key_facts=[],
                    sources=[],
                    confidence=0.0,
                    search_queries_used=[],
                )))

    # Sort by original index
    results.sort(key=lambda x: x[0])

    return [r[1] for r in results]
