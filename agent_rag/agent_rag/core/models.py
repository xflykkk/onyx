"""Core data models for Agent RAG."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents a tool call made by the LLM."""
    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.tool_call_id,
            "type": "function",
            "function": {
                "name": self.tool_name,
                "arguments": self.arguments,
            }
        }


@dataclass
class Citation:
    """Represents a citation to a source document."""
    citation_num: int
    document_id: str
    chunk_id: int
    content: str
    title: Optional[str] = None
    link: Optional[str] = None
    source_type: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "citation_num": self.citation_num,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "title": self.title,
            "link": self.link,
            "source_type": self.source_type,
        }


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str
    content: str
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    citations: Optional[list[Citation]] = None

    def to_llm_message(self) -> dict[str, Any]:
        """Convert to LLM message format."""
        msg: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_calls:
            msg["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


@dataclass
class AgentResponse:
    """Response from an agent."""
    content: str
    citations: list[Citation] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: Optional[str] = None

    # Deep Research specific fields
    research_plan: Optional[str] = None
    intermediate_reports: Optional[list[str]] = None
    is_clarification: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "content": self.content,
            "citations": [c.to_dict() for c in self.citations],
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
        }
        if self.reasoning:
            result["reasoning"] = self.reasoning
        if self.research_plan:
            result["research_plan"] = self.research_plan
        if self.intermediate_reports:
            result["intermediate_reports"] = self.intermediate_reports
        if self.is_clarification:
            result["is_clarification"] = self.is_clarification
        return result


@dataclass
class Chunk:
    """Represents a document chunk."""
    document_id: str
    chunk_id: int
    content: str
    embedding: Optional[list[float]] = None

    # Metadata
    title: Optional[str] = None
    source_type: Optional[str] = None
    link: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Search result fields
    score: float = 0.0
    match_highlights: list[str] = field(default_factory=list)

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def unique_id(self) -> str:
        """Get unique identifier for this chunk."""
        return f"{self.document_id}_{self.chunk_id}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "title": self.title,
            "source_type": self.source_type,
            "link": self.link,
            "metadata": self.metadata,
            "score": self.score,
        }


@dataclass
class Section:
    """Represents a section of a document (multiple consecutive chunks)."""
    center_chunk: Chunk
    chunks: list[Chunk]
    combined_content: str

    @property
    def document_id(self) -> str:
        """Get document ID."""
        return self.center_chunk.document_id

    @property
    def start_chunk_id(self) -> int:
        """Get starting chunk ID."""
        return min(c.chunk_id for c in self.chunks)

    @property
    def end_chunk_id(self) -> int:
        """Get ending chunk ID."""
        return max(c.chunk_id for c in self.chunks)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "document_id": self.document_id,
            "start_chunk_id": self.start_chunk_id,
            "end_chunk_id": self.end_chunk_id,
            "combined_content": self.combined_content,
            "center_chunk": self.center_chunk.to_dict(),
        }


@dataclass
class SearchFilters:
    """Filters for document search."""
    source_types: Optional[list[str]] = None
    time_cutoff: Optional[datetime] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    document_ids: Optional[list[str]] = None

    # Extension point for custom filters
    custom_filters: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result: dict[str, Any] = {}
        if self.source_types:
            result["source_types"] = self.source_types
        if self.time_cutoff:
            result["time_cutoff"] = self.time_cutoff.isoformat()
        if self.tags:
            result["tags"] = self.tags
        if self.metadata:
            result["metadata"] = self.metadata
        if self.document_ids:
            result["document_ids"] = self.document_ids
        if self.custom_filters:
            result["custom_filters"] = self.custom_filters
        return result


@dataclass
class SearchResult:
    """Result from a search operation."""
    chunks: list[Chunk]
    sections: list[Section] = field(default_factory=list)
    total_hits: int = 0
    query: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "sections": [s.to_dict() for s in self.sections],
            "total_hits": self.total_hits,
            "query": self.query,
        }
