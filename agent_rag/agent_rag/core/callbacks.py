"""Callback interfaces for Agent RAG."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from agent_rag.core.models import Chunk, Citation


@dataclass
class StreamEvent:
    """Event for streaming responses."""
    event_type: str
    data: Any
    metadata: Optional[dict[str, Any]] = None


class StreamCallback(ABC):
    """Abstract callback for streaming events."""

    @abstractmethod
    def on_token(self, token: str) -> None:
        """Called when a new token is generated."""
        pass

    def on_stream_start(self) -> None:
        """Called when streaming starts."""
        pass

    def on_stream_end(self) -> None:
        """Called when streaming ends."""
        pass


class ToolCallback(ABC):
    """Abstract callback for tool events."""

    @abstractmethod
    def on_tool_start(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Called when a tool execution starts."""
        pass

    @abstractmethod
    def on_tool_end(self, tool_name: str, result: Any) -> None:
        """Called when a tool execution ends."""
        pass

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Called when a tool execution fails."""
        pass


class ReasoningCallback(ABC):
    """Abstract callback for reasoning events."""

    @abstractmethod
    def on_reasoning_start(self) -> None:
        """Called when reasoning starts."""
        pass

    @abstractmethod
    def on_reasoning_token(self, token: str) -> None:
        """Called for each reasoning token."""
        pass

    def on_reasoning_end(self, full_reasoning: str) -> None:
        """Called when reasoning ends."""
        pass


class CitationCallback(ABC):
    """Abstract callback for citation events."""

    @abstractmethod
    def on_citation(self, citation: Citation) -> None:
        """Called when a citation is added."""
        pass


class SearchCallback(ABC):
    """Abstract callback for search events."""

    @abstractmethod
    def on_search_start(self, query: str) -> None:
        """Called when a search starts."""
        pass

    @abstractmethod
    def on_search_results(self, chunks: list[Chunk]) -> None:
        """Called when search results are available."""
        pass

    def on_search_end(self) -> None:
        """Called when search ends."""
        pass


class DeepResearchCallback(ABC):
    """Abstract callback for Deep Research events."""

    def on_clarification_needed(self, question: str) -> None:
        """Called when clarification is needed from user."""
        pass

    @abstractmethod
    def on_research_plan(self, plan: str) -> None:
        """Called when research plan is generated."""
        pass

    @abstractmethod
    def on_research_agent_start(self, agent_index: int, task: str) -> None:
        """Called when a research agent starts."""
        pass

    @abstractmethod
    def on_intermediate_report(self, agent_index: int, report: str) -> None:
        """Called when an intermediate report is generated."""
        pass

    def on_final_report_start(self) -> None:
        """Called when final report generation starts."""
        pass


class AgentCallback(
    StreamCallback,
    ToolCallback,
    ReasoningCallback,
    CitationCallback,
    ABC
):
    """Combined callback interface for all agent events."""

    def on_cycle_start(self, cycle_num: int) -> None:
        """Called at the start of each agent cycle."""
        pass

    def on_cycle_end(self, cycle_num: int) -> None:
        """Called at the end of each agent cycle."""
        pass


class PrintCallback(AgentCallback):
    """Simple callback that prints events to console."""

    def on_token(self, token: str) -> None:
        print(token, end="", flush=True)

    def on_stream_start(self) -> None:
        pass

    def on_stream_end(self) -> None:
        print()

    def on_tool_start(self, tool_name: str, arguments: dict[str, Any]) -> None:
        print(f"\n[Tool: {tool_name}] Starting...")

    def on_tool_end(self, tool_name: str, result: Any) -> None:
        print(f"[Tool: {tool_name}] Done")

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        print(f"[Tool: {tool_name}] Error: {error}")

    def on_reasoning_start(self) -> None:
        print("\n[Thinking...]")

    def on_reasoning_token(self, token: str) -> None:
        pass  # Don't print reasoning tokens by default

    def on_reasoning_end(self, full_reasoning: str) -> None:
        pass

    def on_citation(self, citation: Citation) -> None:
        pass  # Citations are embedded in the response


class CallbackHandler:
    """Handler that manages multiple callbacks."""

    def __init__(self) -> None:
        self._callbacks: list[AgentCallback] = []

    def add_callback(self, callback: AgentCallback) -> None:
        """Add a callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: AgentCallback) -> None:
        """Remove a callback."""
        self._callbacks.remove(callback)

    def on_token(self, token: str) -> None:
        """Dispatch token event to all callbacks."""
        for cb in self._callbacks:
            cb.on_token(token)

    def on_stream_start(self) -> None:
        """Dispatch stream start event."""
        for cb in self._callbacks:
            cb.on_stream_start()

    def on_stream_end(self) -> None:
        """Dispatch stream end event."""
        for cb in self._callbacks:
            cb.on_stream_end()

    def on_tool_start(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Dispatch tool start event."""
        for cb in self._callbacks:
            cb.on_tool_start(tool_name, arguments)

    def on_tool_end(self, tool_name: str, result: Any) -> None:
        """Dispatch tool end event."""
        for cb in self._callbacks:
            cb.on_tool_end(tool_name, result)

    def on_tool_error(self, tool_name: str, error: Exception) -> None:
        """Dispatch tool error event."""
        for cb in self._callbacks:
            cb.on_tool_error(tool_name, error)

    def on_reasoning_start(self) -> None:
        """Dispatch reasoning start event."""
        for cb in self._callbacks:
            cb.on_reasoning_start()

    def on_reasoning_token(self, token: str) -> None:
        """Dispatch reasoning token event."""
        for cb in self._callbacks:
            cb.on_reasoning_token(token)

    def on_reasoning_end(self, full_reasoning: str) -> None:
        """Dispatch reasoning end event."""
        for cb in self._callbacks:
            cb.on_reasoning_end(full_reasoning)

    def on_citation(self, citation: Citation) -> None:
        """Dispatch citation event."""
        for cb in self._callbacks:
            cb.on_citation(citation)

    def on_cycle_start(self, cycle_num: int) -> None:
        """Dispatch cycle start event."""
        for cb in self._callbacks:
            cb.on_cycle_start(cycle_num)

    def on_cycle_end(self, cycle_num: int) -> None:
        """Dispatch cycle end event."""
        for cb in self._callbacks:
            cb.on_cycle_end(cycle_num)
