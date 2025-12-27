"""Custom exceptions for Agent RAG."""

from typing import Any, Optional


class AgentRAGError(Exception):
    """Base exception for Agent RAG."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class ConfigurationError(AgentRAGError):
    """Raised when there's a configuration error."""
    pass


class LLMError(AgentRAGError):
    """Raised when there's an LLM-related error."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.model = model
        self.provider = provider


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class LLMContextLengthError(LLMError):
    """Raised when input exceeds LLM context length."""

    def __init__(
        self,
        message: str = "Context length exceeded",
        max_tokens: Optional[int] = None,
        actual_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.max_tokens = max_tokens
        self.actual_tokens = actual_tokens


class ToolError(AgentRAGError):
    """Raised when there's a tool-related error."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.tool_name = tool_name


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool not found: {tool_name}", tool_name=tool_name)


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        original_error: Optional[Exception] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, tool_name=tool_name, details=details)
        self.original_error = original_error


class RetrievalError(AgentRAGError):
    """Raised when there's a retrieval-related error."""
    pass


class DocumentIndexError(RetrievalError):
    """Raised when there's a document index error."""

    def __init__(
        self,
        message: str,
        index_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.index_type = index_type


class EmbeddingError(RetrievalError):
    """Raised when there's an embedding error."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.model = model


class SearchError(RetrievalError):
    """Raised when there's a search error."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.query = query


class AgentCycleError(AgentRAGError):
    """Raised when agent exceeds maximum cycles."""

    def __init__(
        self,
        message: str = "Maximum agent cycles exceeded",
        max_cycles: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.max_cycles = max_cycles


class DeepResearchError(AgentRAGError):
    """Raised when there's a Deep Research error."""
    pass


class ResearchAgentError(DeepResearchError):
    """Raised when a research agent fails."""

    def __init__(
        self,
        message: str,
        agent_index: Optional[int] = None,
        task: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, details)
        self.agent_index = agent_index
        self.task = task
