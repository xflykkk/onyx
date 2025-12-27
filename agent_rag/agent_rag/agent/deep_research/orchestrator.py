"""Deep Research Orchestrator.

Coordinates the deep research process:
1. Analyze question and generate sub-questions
2. Spawn parallel research agents
3. Collect and synthesize findings
4. Generate comprehensive report
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterator, Optional

from agent_rag.agent.deep_research.report_generator import (
    ReportConfig,
    ReportGenerator,
    ResearchReport,
    format_report_markdown,
)
from agent_rag.agent.deep_research.research_agent import (
    ResearchAgent,
    ResearchAgentConfig,
    ResearchFindings,
    run_research_agents_parallel,
)
from agent_rag.agent.deep_research.think_tool import ThinkTool
from agent_rag.core.config import DeepResearchConfig
from agent_rag.llm.interface import LLM, LLMMessage
from agent_rag.tools.registry import ToolRegistry
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


class OrchestratorState(Enum):
    """States of the orchestrator."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    RESEARCHING = "researching"
    SYNTHESIZING = "synthesizing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class OrchestratorProgress:
    """Progress update from orchestrator."""
    state: OrchestratorState
    cycle: int
    total_cycles: int
    message: str
    sub_questions: list[str] = field(default_factory=list)
    completed_agents: int = 0
    total_agents: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


QUESTION_ANALYSIS_PROMPT = """You are a research planner. Analyze the following research question and break it down into focused sub-questions that can be researched independently.

Research Question: {question}

Generate {num_subquestions} specific sub-questions that:
1. Together comprehensively cover the main question
2. Can be researched independently
3. Are specific and focused
4. Don't overlap significantly

Respond with just the sub-questions, one per line, numbered:
1. [sub-question 1]
2. [sub-question 2]
...
"""


class DeepResearchOrchestrator:
    """
    Orchestrates the deep research process.

    The orchestrator:
    1. Analyzes the research question
    2. Generates focused sub-questions
    3. Spawns parallel research agents
    4. Collects findings using Think tool
    5. Decides if more research is needed
    6. Generates final report

    Max cycles: 8 (configurable)
    Research agents per cycle: 3 (configurable)
    Agent cycles: 3 each
    """

    def __init__(
        self,
        llm: LLM,
        tool_registry: ToolRegistry,
        config: Optional[DeepResearchConfig] = None,
        progress_callback: Optional[Callable[[OrchestratorProgress], None]] = None,
    ) -> None:
        """
        Initialize the orchestrator.

        Args:
            llm: LLM provider
            tool_registry: Registry of available tools
            config: Deep research configuration
            progress_callback: Callback for progress updates
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.config = config or DeepResearchConfig()
        self.progress_callback = progress_callback

        # Components
        self.think_tool = ThinkTool(llm=llm)
        self.report_generator = ReportGenerator(llm=llm)

        # State
        self.state = OrchestratorState.IDLE
        self.current_cycle = 0
        self.all_findings: list[ResearchFindings] = []
        self.sub_questions_history: list[str] = []

    def reset(self) -> None:
        """Reset orchestrator state."""
        self.state = OrchestratorState.IDLE
        self.current_cycle = 0
        self.all_findings = []
        self.sub_questions_history = []

    def research(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ResearchReport:
        """
        Conduct deep research on a question.

        Args:
            question: Research question
            context: Optional context for tools

        Returns:
            Comprehensive research report
        """
        self.reset()
        self._notify_progress(
            OrchestratorState.ANALYZING,
            "Analyzing research question...",
        )

        try:
            # Main research loop
            while self.current_cycle < self.config.max_orchestrator_cycles:
                self.current_cycle += 1

                # Generate or refine sub-questions
                if self.current_cycle == 1:
                    sub_questions = self._generate_initial_subquestions(question)
                else:
                    sub_questions = self._generate_refined_subquestions(question)

                if not sub_questions:
                    logger.warning("No sub-questions generated, ending research")
                    break

                self.sub_questions_history.extend(sub_questions)

                # Run research agents
                self._notify_progress(
                    OrchestratorState.RESEARCHING,
                    f"Cycle {self.current_cycle}: Researching {len(sub_questions)} sub-questions...",
                    sub_questions=sub_questions,
                )

                findings = self._run_research_cycle(
                    sub_questions=sub_questions,
                    main_question=question,
                    context=context,
                )
                self.all_findings.extend(findings)

                # Think about findings
                think_result = self._think_about_findings(question)

                if think_result.has_sufficient_info:
                    logger.info("Sufficient information gathered, generating report")
                    break

                if not think_result.refined_queries:
                    logger.info("No more refined queries, ending research")
                    break

            # Generate report
            self._notify_progress(
                OrchestratorState.SYNTHESIZING,
                "Synthesizing findings into report...",
            )

            report = self.report_generator.generate(
                question=question,
                findings=self.all_findings,
                context=context,
            )

            self._notify_progress(
                OrchestratorState.COMPLETE,
                "Research complete!",
            )

            return report

        except Exception as e:
            self.state = OrchestratorState.FAILED
            self._notify_progress(
                OrchestratorState.FAILED,
                f"Research failed: {str(e)}",
            )
            raise

    def research_stream(
        self,
        question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Iterator[tuple[str, Optional[ResearchReport]]]:
        """
        Conduct deep research with streaming output.

        Args:
            question: Research question
            context: Optional context

        Yields:
            Tuples of (update_text, final_report) where report is None until complete
        """
        self.reset()

        yield ("Analyzing research question...\n", None)

        try:
            while self.current_cycle < self.config.max_orchestrator_cycles:
                self.current_cycle += 1

                if self.current_cycle == 1:
                    sub_questions = self._generate_initial_subquestions(question)
                else:
                    sub_questions = self._generate_refined_subquestions(question)

                if not sub_questions:
                    break

                self.sub_questions_history.extend(sub_questions)

                yield (f"\n## Cycle {self.current_cycle}\n", None)
                yield (f"Researching {len(sub_questions)} sub-questions:\n", None)
                for i, sq in enumerate(sub_questions, 1):
                    yield (f"  {i}. {sq}\n", None)

                findings = self._run_research_cycle(
                    sub_questions=sub_questions,
                    main_question=question,
                    context=context,
                )
                self.all_findings.extend(findings)

                # Report findings
                for finding in findings:
                    yield (f"\n### {finding.sub_question}\n", None)
                    yield (f"{finding.summary[:200]}...\n", None)

                think_result = self._think_about_findings(question)

                if think_result.has_sufficient_info:
                    yield ("\nSufficient information gathered.\n", None)
                    break

            # Generate report with streaming
            yield ("\n---\n\n# Generating Report\n\n", None)

            report = None
            for token, final_report in self.report_generator.generate_stream(
                question=question,
                findings=self.all_findings,
                context=context,
            ):
                if token:
                    yield (token, None)
                if final_report:
                    report = final_report

            yield ("", report)

        except Exception as e:
            yield (f"\nError: {str(e)}\n", None)
            raise

    def _generate_initial_subquestions(self, question: str) -> list[str]:
        """Generate initial sub-questions from main question."""
        prompt = QUESTION_ANALYSIS_PROMPT.format(
            question=question,
            num_subquestions=self.config.num_research_agents,
        )

        messages = [LLMMessage(role="user", content=prompt)]
        response = self.llm.generate(messages)

        return self._parse_subquestions(response.content)

    def _generate_refined_subquestions(self, question: str) -> list[str]:
        """Generate refined sub-questions based on current findings."""
        think_result = self.think_tool.think(
            question=question,
            current_findings=self._summarize_findings(),
            search_history=self.sub_questions_history,
            max_queries=self.config.num_research_agents,
        )

        return think_result.refined_queries

    def _run_research_cycle(
        self,
        sub_questions: list[str],
        main_question: str,
        context: Optional[dict[str, Any]] = None,
    ) -> list[ResearchFindings]:
        """Run a cycle of parallel research agents."""
        # Create agents
        agents = []
        for i, sq in enumerate(sub_questions):
            agent = ResearchAgent(
                llm=self.llm,
                tool_registry=self.tool_registry,
                config=ResearchAgentConfig(
                    max_cycles=self.config.max_agent_cycles,
                ),
                agent_id=f"agent_{self.current_cycle}_{i}",
            )
            agents.append(agent)

        # Run in parallel
        findings = run_research_agents_parallel(
            agents=agents,
            sub_questions=sub_questions,
            main_question=main_question,
            context=context,
            max_workers=self.config.num_research_agents,
        )

        return findings

    def _think_about_findings(self, question: str) -> Any:
        """Use think tool to analyze current findings."""
        return self.think_tool.think(
            question=question,
            current_findings=self._summarize_findings(),
            search_history=self.sub_questions_history,
        )

    def _summarize_findings(self) -> str:
        """Summarize all current findings."""
        if not self.all_findings:
            return "No findings yet."

        summaries = []
        for finding in self.all_findings:
            summaries.append(f"**{finding.sub_question}**: {finding.summary[:200]}...")

        return "\n\n".join(summaries)

    def _parse_subquestions(self, text: str) -> list[str]:
        """Parse sub-questions from LLM response."""
        import re

        questions = []
        for line in text.split('\n'):
            line = line.strip()
            # Match numbered questions
            match = re.match(r'^\d+[\.\)]\s*(.+)$', line)
            if match:
                question = match.group(1).strip()
                if question:
                    questions.append(question)

        return questions[:self.config.num_research_agents]

    def _notify_progress(
        self,
        state: OrchestratorState,
        message: str,
        sub_questions: Optional[list[str]] = None,
    ) -> None:
        """Notify progress callback."""
        self.state = state

        if self.progress_callback:
            progress = OrchestratorProgress(
                state=state,
                cycle=self.current_cycle,
                total_cycles=self.config.max_orchestrator_cycles,
                message=message,
                sub_questions=sub_questions or [],
                completed_agents=len(self.all_findings),
                total_agents=len(self.sub_questions_history),
            )
            self.progress_callback(progress)


def create_deep_research_agent(
    llm: LLM,
    tool_registry: ToolRegistry,
    config: Optional[DeepResearchConfig] = None,
) -> DeepResearchOrchestrator:
    """Factory function to create a deep research orchestrator."""
    return DeepResearchOrchestrator(
        llm=llm,
        tool_registry=tool_registry,
        config=config,
    )
