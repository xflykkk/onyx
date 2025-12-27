"""Agent step execution for Agent RAG."""

from dataclasses import dataclass
from typing import Any, Iterator, Optional

from agent_rag.core.models import Message, ToolCall
from agent_rag.llm.interface import LLM, LLMMessage
from agent_rag.tools.registry import ToolRegistry
from agent_rag.tools.runner import ToolRunner
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StepResult:
    """Result of a single agent step."""
    content: str
    tool_calls: list[ToolCall]
    should_continue: bool
    tokens_used: int = 0
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AgentStep:
    """
    Executes a single step in the agent loop.

    A step consists of:
    1. Calling LLM with current messages
    2. Processing any tool calls
    3. Returning result with continuation decision
    """

    def __init__(
        self,
        llm: LLM,
        tool_registry: ToolRegistry,
        tool_runner: Optional[ToolRunner] = None,
    ) -> None:
        """
        Initialize the step executor.

        Args:
            llm: LLM provider
            tool_registry: Registry of available tools
            tool_runner: Optional tool runner (created if not provided)
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.tool_runner = tool_runner or ToolRunner(tool_registry)

    def _messages_to_llm_format(
        self,
        messages: list[Message],
    ) -> list[LLMMessage]:
        """Convert Message objects to LLMMessage format."""
        return [
            LLMMessage(
                role=msg.role,
                content=msg.content,
                tool_calls=[
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in (msg.tool_calls or [])
                ] if msg.tool_calls else None,
                tool_call_id=msg.tool_call_id,
            )
            for msg in messages
        ]

    def execute(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        force_tool: Optional[str] = None,
    ) -> StepResult:
        """
        Execute a single step.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions (uses registry if not provided)
            force_tool: Optional tool name to force

        Returns:
            StepResult with content and tool calls
        """
        # Get tool definitions
        if tools is None:
            tools = self.tool_registry.get_all_definitions()

        # Convert messages
        llm_messages = self._messages_to_llm_format(messages)

        # Build tool choice
        tool_choice = None
        if force_tool:
            tool_choice = {"type": "function", "function": {"name": force_tool}}
        elif tools:
            tool_choice = "auto"

        # Call LLM
        response = self.llm.generate(
            messages=llm_messages,
            tools=tools if tools else None,
            tool_choice=tool_choice,
        )

        # Extract tool calls
        tool_calls: list[ToolCall] = []
        if response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=tc.get("function", {}).get("arguments", "{}"),
                ))

        # Determine if we should continue
        should_continue = len(tool_calls) > 0

        return StepResult(
            content=response.content,
            tool_calls=tool_calls,
            should_continue=should_continue,
            tokens_used=response.usage.get("total_tokens", 0) if response.usage else 0,
        )

    def execute_stream(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> Iterator[tuple[str, Optional[StepResult]]]:
        """
        Execute a step with streaming.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions

        Yields:
            Tuples of (token, final_result) where final_result is None until complete
        """
        if tools is None:
            tools = self.tool_registry.get_all_definitions()

        llm_messages = self._messages_to_llm_format(messages)

        tool_choice = "auto" if tools else None

        # Accumulate response
        full_content = ""
        tool_calls: list[ToolCall] = []
        tokens_used = 0

        for chunk in self.llm.generate_stream(
            messages=llm_messages,
            tools=tools if tools else None,
            tool_choice=tool_choice,
        ):
            if chunk.content:
                full_content += chunk.content
                yield (chunk.content, None)

            if chunk.tool_calls:
                for tc in chunk.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.get("id", ""),
                        name=tc.get("function", {}).get("name", ""),
                        arguments=tc.get("function", {}).get("arguments", "{}"),
                    ))

            if chunk.usage:
                tokens_used = chunk.usage.get("total_tokens", 0)

        # Yield final result
        result = StepResult(
            content=full_content,
            tool_calls=tool_calls,
            should_continue=len(tool_calls) > 0,
            tokens_used=tokens_used,
        )
        yield ("", result)

    def execute_tools(
        self,
        tool_calls: list[ToolCall],
        context: Optional[dict[str, Any]] = None,
    ) -> list[tuple[ToolCall, str]]:
        """
        Execute tool calls and return results.

        Args:
            tool_calls: Tool calls to execute
            context: Optional context for tools

        Returns:
            List of (tool_call, result_string) tuples
        """
        results: list[tuple[ToolCall, str]] = []

        for tool_call in tool_calls:
            try:
                result = self.tool_runner.run(
                    tool_call.name,
                    tool_call.parsed_arguments,
                    context=context,
                )
                results.append((tool_call, result.llm_response))
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_call.name}: {e}")
                results.append((tool_call, f"Error: {str(e)}"))

        return results

    def execute_tools_parallel(
        self,
        tool_calls: list[ToolCall],
        context: Optional[dict[str, Any]] = None,
        max_workers: int = 5,
    ) -> list[tuple[ToolCall, str]]:
        """
        Execute tool calls in parallel.

        Args:
            tool_calls: Tool calls to execute
            context: Optional context for tools
            max_workers: Maximum parallel workers

        Returns:
            List of (tool_call, result_string) tuples
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: list[tuple[ToolCall, str]] = []

        def execute_single(tc: ToolCall) -> tuple[ToolCall, str]:
            try:
                result = self.tool_runner.run(
                    tc.name,
                    tc.parsed_arguments,
                    context=context,
                )
                return (tc, result.llm_response)
            except Exception as e:
                logger.error(f"Tool execution failed: {tc.name}: {e}")
                return (tc, f"Error: {str(e)}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(execute_single, tc): tc
                for tc in tool_calls
            }

            for future in as_completed(futures):
                results.append(future.result())

        # Sort by original order
        tc_order = {tc.id: i for i, tc in enumerate(tool_calls)}
        results.sort(key=lambda x: tc_order.get(x[0].id, 0))

        return results
