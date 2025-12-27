"""Tool registry for Agent RAG."""

from typing import Any, Optional

from agent_rag.tools.interface import Tool
from agent_rag.core.exceptions import ToolNotFoundError
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool[Any]] = {}
        self._next_id = 1

    def register(self, tool: Tool[Any]) -> None:
        """
        Register a tool.

        Args:
            tool: Tool to register
        """
        if tool._id is None:
            tool._id = self._next_id
            self._next_id += 1

        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if tool was unregistered
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Tool[Any]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            ToolNotFoundError: If tool not found
        """
        if name not in self._tools:
            raise ToolNotFoundError(name)
        return self._tools[name]

    def get_optional(self, name: str) -> Optional[Tool[Any]]:
        """
        Get a tool by name, returning None if not found.

        Args:
            name: Tool name

        Returns:
            Tool instance or None
        """
        return self._tools.get(name)

    def list_tools(self) -> list[Tool[Any]]:
        """
        List all registered tools.

        Returns:
            List of tools
        """
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_tool_definitions(
        self,
        tool_names: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Get tool definitions for specified tools (or all).

        Args:
            tool_names: Optional list of tool names to include

        Returns:
            List of tool definitions
        """
        tools = self.list_tools()

        if tool_names:
            tools = [t for t in tools if t.name in tool_names]

        return [t.tool_definition() for t in tools]

    def has(self, name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool is registered
        """
        return name in self._tools

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._next_id = 1
