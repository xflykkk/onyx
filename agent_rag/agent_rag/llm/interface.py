"""LLM interface definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator, Optional

from agent_rag.core.config import LLMConfig, ToolChoice


@dataclass
class LLMMessage:
    """Message for LLM conversation."""
    role: str
    content: str
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for LLM API."""
        msg: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.name:
            msg["name"] = self.name
        return msg


@dataclass
class LLMToolCall:
    """Tool call from LLM response."""
    id: str
    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments,
            }
        }


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    reasoning: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[dict[str, int]] = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response has tool calls."""
        return len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """Chunk from streaming LLM response."""
    content: str = ""
    reasoning: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None
    is_reasoning: bool = False


class LLM(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.model

    @property
    def is_reasoning_model(self) -> bool:
        """Check if this is a reasoning model."""
        return self.config.is_reasoning_model

    @abstractmethod
    def chat(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """
        Synchronous chat completion.

        Args:
            messages: List of messages
            tools: Optional list of tool definitions
            tool_choice: Tool choice mode
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLM response
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[StreamChunk, None, LLMResponse]:
        """
        Streaming chat completion.

        Args:
            messages: List of messages
            tools: Optional list of tool definitions
            tool_choice: Tool choice mode
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Stream chunks

        Returns:
            Final LLM response
        """
        pass

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        # Default implementation: ~4 characters per token
        return len(text) // 4

    def count_message_tokens(self, messages: list[LLMMessage]) -> int:
        """
        Count tokens in messages.

        Args:
            messages: Messages to count tokens for

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            # Role overhead
            total += 4
            # Content
            total += self.count_tokens(msg.content)
            # Tool calls
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += self.count_tokens(str(tc))
        return total

    def truncate_to_fit(
        self,
        messages: list[LLMMessage],
        max_tokens: Optional[int] = None,
        reserve_tokens: int = 1000,
    ) -> list[LLMMessage]:
        """
        Truncate messages to fit within token limit.

        Args:
            messages: Messages to truncate
            max_tokens: Maximum tokens (defaults to config)
            reserve_tokens: Tokens to reserve for response

        Returns:
            Truncated messages
        """
        max_tokens = max_tokens or self.config.max_input_tokens
        target_tokens = max_tokens - reserve_tokens

        # Always keep system message if present
        system_msg = None
        other_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg
            else:
                other_messages.append(msg)

        # Count system message tokens
        current_tokens = 0
        if system_msg:
            current_tokens += self.count_tokens(system_msg.content) + 4

        # Add messages from the end (most recent first)
        result_messages: list[LLMMessage] = []
        for msg in reversed(other_messages):
            msg_tokens = self.count_tokens(msg.content) + 4
            if msg.tool_calls:
                msg_tokens += self.count_tokens(str(msg.tool_calls))

            if current_tokens + msg_tokens <= target_tokens:
                result_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        # Add system message at the beginning
        if system_msg:
            result_messages.insert(0, system_msg)

        return result_messages
