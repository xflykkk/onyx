"""Tool runner for Agent RAG."""

from typing import Any, Callable, Optional

from agent_rag.core.exceptions import ToolError, ToolExecutionError, ToolNotFoundError
from agent_rag.core.models import ToolCall
from agent_rag.tools.interface import Tool, ToolResponse
from agent_rag.tools.registry import ToolRegistry
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRunner:
    """Runs tools and manages execution."""

    def __init__(
        self,
        registry: ToolRegistry,
        on_tool_start: Optional[Callable[[str, dict[str, Any]], None]] = None,
        on_tool_end: Optional[Callable[[str, ToolResponse], None]] = None,
        on_tool_error: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        self.registry = registry
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_tool_error = on_tool_error

    def run(
        self,
        tool_call: ToolCall,
        override_kwargs: Optional[Any] = None,
    ) -> ToolResponse:
        """
        Run a single tool call.

        Args:
            tool_call: Tool call to execute
            override_kwargs: Optional override arguments

        Returns:
            Tool response
        """
        tool_name = tool_call.tool_name
        arguments = tool_call.arguments

        # Notify start
        if self.on_tool_start:
            self.on_tool_start(tool_name, arguments)

        try:
            # Get tool
            tool = self.registry.get(tool_name)

            # Execute
            response = tool.run(override_kwargs, **arguments)

            # Notify end
            if self.on_tool_end:
                self.on_tool_end(tool_name, response)

            return response

        except ToolNotFoundError:
            error = ToolNotFoundError(tool_name)
            if self.on_tool_error:
                self.on_tool_error(tool_name, error)
            raise

        except Exception as e:
            error = ToolExecutionError(
                message=str(e),
                tool_name=tool_name,
                original_error=e,
            )
            if self.on_tool_error:
                self.on_tool_error(tool_name, error)
            raise error

    def run_many(
        self,
        tool_calls: list[ToolCall],
        override_kwargs: Optional[dict[str, Any]] = None,
        continue_on_error: bool = False,
    ) -> list[tuple[ToolCall, ToolResponse | Exception]]:
        """
        Run multiple tool calls.

        Args:
            tool_calls: Tool calls to execute
            override_kwargs: Dict of tool_name -> override_kwargs
            continue_on_error: Whether to continue on errors

        Returns:
            List of (tool_call, response_or_error) tuples
        """
        override_kwargs = override_kwargs or {}
        results: list[tuple[ToolCall, ToolResponse | Exception]] = []

        for tool_call in tool_calls:
            try:
                override = override_kwargs.get(tool_call.tool_name)
                response = self.run(tool_call, override)
                results.append((tool_call, response))
            except Exception as e:
                if continue_on_error:
                    results.append((tool_call, e))
                else:
                    raise

        return results

    def get_tool_definitions(
        self,
        tool_names: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Get tool definitions.

        Args:
            tool_names: Optional list of tool names

        Returns:
            List of tool definitions
        """
        return self.registry.get_tool_definitions(tool_names)


def create_tool_error_response(
    tool_name: str,
    error: Exception,
) -> ToolResponse:
    """
    Create an error response for a tool.

    Args:
        tool_name: Tool name
        error: Exception that occurred

    Returns:
        Tool response with error message
    """
    return ToolResponse(
        llm_response=f"Error executing {tool_name}: {str(error)}",
    )
