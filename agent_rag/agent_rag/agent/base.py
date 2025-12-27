"""Base agent class for Agent RAG."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterator, Optional

from agent_rag.core.callbacks import AgentCallback, StreamCallback, ToolCallback
from agent_rag.core.config import AgentConfig
from agent_rag.core.models import AgentResponse, Message, ToolCall
from agent_rag.llm.interface import LLM
from agent_rag.tools.registry import ToolRegistry
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentState:
    """State maintained during agent execution."""
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    step_count: int = 0
    total_tokens: int = 0
    should_stop: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all agents in Agent RAG.

    Provides:
    - Unified interface for agent execution
    - Message and state management
    - Tool execution coordination
    - Callback hooks for extensibility
    """

    def __init__(
        self,
        llm: LLM,
        config: Optional[AgentConfig] = None,
        tool_registry: Optional[ToolRegistry] = None,
        stream_callback: Optional[StreamCallback] = None,
        tool_callback: Optional[ToolCallback] = None,
        agent_callback: Optional[AgentCallback] = None,
    ) -> None:
        """
        Initialize the agent.

        Args:
            llm: LLM provider for generating responses
            config: Agent configuration
            tool_registry: Registry of available tools
            stream_callback: Callback for streaming tokens
            tool_callback: Callback for tool execution events
            agent_callback: Callback for agent lifecycle events
        """
        self.llm = llm
        self.config = config or AgentConfig()
        self.tool_registry = tool_registry or ToolRegistry()
        self.stream_callback = stream_callback
        self.tool_callback = tool_callback
        self.agent_callback = agent_callback

        self._state: Optional[AgentState] = None

    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        if self._state is None:
            self._state = AgentState()
        return self._state

    def reset(self) -> None:
        """Reset agent state."""
        self._state = AgentState()

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.state.messages.append(message)

    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        self.add_message(Message(role="system", content=content))

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message(Message(role="user", content=content))

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[list[ToolCall]] = None,
    ) -> None:
        """Add an assistant message."""
        self.add_message(Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
        ))

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        """Add a tool result message."""
        self.add_message(Message(
            role="tool",
            content=result,
            tool_call_id=tool_call_id,
        ))

    @abstractmethod
    def run(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Run the agent with the given query.

        Args:
            query: User query
            context: Optional context for the agent

        Returns:
            AgentResponse with the result
        """

    @abstractmethod
    def run_stream(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Iterator[str]:
        """
        Run the agent with streaming output.

        Args:
            query: User query
            context: Optional context for the agent

        Yields:
            Response tokens
        """

    async def arun(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Async version of run.

        Default implementation wraps sync run.
        Override for true async behavior.
        """
        return self.run(query, context)

    async def arun_stream(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        Async version of run_stream.

        Default implementation wraps sync run_stream.
        Override for true async behavior.
        """
        for token in self.run_stream(query, context):
            yield token

    def should_continue(self) -> bool:
        """Check if agent should continue execution."""
        if self.state.should_stop:
            return False

        if self.state.step_count >= self.config.max_steps:
            logger.warning(
                f"Agent reached max steps ({self.config.max_steps})"
            )
            return False

        if self.config.max_tokens and self.state.total_tokens >= self.config.max_tokens:
            logger.warning(
                f"Agent reached max tokens ({self.config.max_tokens})"
            )
            return False

        return True

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get tool definitions for LLM."""
        return self.tool_registry.get_all_definitions()

    def _notify_start(self, query: str) -> None:
        """Notify callbacks of agent start."""
        if self.agent_callback:
            self.agent_callback.on_agent_start(query)

    def _notify_end(self, response: AgentResponse) -> None:
        """Notify callbacks of agent end."""
        if self.agent_callback:
            self.agent_callback.on_agent_end(response)

    def _notify_error(self, error: Exception) -> None:
        """Notify callbacks of agent error."""
        if self.agent_callback:
            self.agent_callback.on_agent_error(error)

    def _notify_step(self, step: int, message: Message) -> None:
        """Notify callbacks of step completion."""
        if self.agent_callback:
            self.agent_callback.on_step_complete(step, message)

    def _stream_token(self, token: str) -> None:
        """Stream a token to callback."""
        if self.stream_callback:
            self.stream_callback.on_token(token)

    def _notify_tool_start(self, tool_call: ToolCall) -> None:
        """Notify callbacks of tool start."""
        if self.tool_callback:
            self.tool_callback.on_tool_start(
                tool_call.name,
                tool_call.arguments,
            )

    def _notify_tool_end(self, tool_call: ToolCall, result: Any) -> None:
        """Notify callbacks of tool end."""
        if self.tool_callback:
            self.tool_callback.on_tool_end(
                tool_call.name,
                result,
            )

    def _notify_tool_error(self, tool_call: ToolCall, error: Exception) -> None:
        """Notify callbacks of tool error."""
        if self.tool_callback:
            self.tool_callback.on_tool_error(
                tool_call.name,
                error,
            )
