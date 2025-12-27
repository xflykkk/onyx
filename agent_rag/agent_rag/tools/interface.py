"""Tool interface definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

TOverride = TypeVar("TOverride")


@dataclass
class ToolResponse:
    """Response from a tool execution."""
    llm_response: str  # Text response for the LLM
    rich_response: Any = None  # Rich response (e.g., search results)
    citation_mapping: dict[int, str] = field(default_factory=dict)  # citation_num -> doc_id

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "llm_response": self.llm_response,
            "citation_mapping": self.citation_mapping,
        }


class Tool(ABC, Generic[TOverride]):
    """Abstract base class for tools."""

    def __init__(self, id: Optional[int] = None) -> None:
        self._id = id

    @property
    def id(self) -> Optional[int]:
        """Get tool ID."""
        return self._id

    @property
    @abstractmethod
    def name(self) -> str:
        """Get tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get tool description."""
        pass

    @abstractmethod
    def tool_definition(self) -> dict[str, Any]:
        """
        Get OpenAI-format tool definition.

        Returns:
            Tool definition dictionary
        """
        pass

    @abstractmethod
    def run(
        self,
        override_kwargs: Optional[TOverride] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """
        Execute the tool.

        Args:
            override_kwargs: Override arguments from configuration
            **llm_kwargs: Arguments from LLM tool call

        Returns:
            Tool response
        """
        pass

    def build_tool_definition(
        self,
        parameters: dict[str, Any],
        required: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Helper to build tool definition.

        Args:
            parameters: Parameter definitions
            required: List of required parameter names

        Returns:
            OpenAI-format tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required or [],
                },
            },
        }


class SimpleTool(Tool[None]):
    """Simple tool without override kwargs."""

    def run(
        self,
        override_kwargs: Optional[None] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Execute the tool."""
        return self._run(**llm_kwargs)

    @abstractmethod
    def _run(self, **kwargs: Any) -> ToolResponse:
        """Internal run method."""
        pass
