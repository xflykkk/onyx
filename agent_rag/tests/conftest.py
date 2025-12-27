"""Pytest configuration and fixtures."""

import pytest
from typing import Any, Iterator, Optional
from unittest.mock import MagicMock

from agent_rag.core.models import Chunk, Message
from agent_rag.llm.interface import LLM, LLMMessage, LLMResponse, StreamChunk
from agent_rag.document_index.interface import DocumentIndex
from agent_rag.tools.interface import Tool, ToolResponse


class MockLLM(LLM):
    """Mock LLM for testing."""

    def __init__(self, responses: Optional[list[str]] = None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0
        self.last_messages: list[LLMMessage] = []

    def generate(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.last_messages = messages
        response_idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1

        return LLMResponse(
            content=self.responses[response_idx],
            tool_calls=None,
            usage={"total_tokens": 100},
        )

    def generate_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        self.last_messages = messages
        response_idx = min(self.call_count, len(self.responses) - 1)
        self.call_count += 1

        response = self.responses[response_idx]
        for char in response:
            yield StreamChunk(content=char, tool_calls=None)


class MockDocumentIndex(DocumentIndex):
    """Mock document index for testing."""

    def __init__(self, chunks: Optional[list[Chunk]] = None):
        self.chunks = chunks or []

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        filters: Optional[Any] = None,
        hybrid_alpha: float = 0.5,
        num_results: int = 10,
    ) -> list[Chunk]:
        return self.chunks[:num_results]

    def semantic_search(
        self,
        query_embedding: list[float],
        filters: Optional[Any] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        return self.chunks[:num_results]

    def keyword_search(
        self,
        query: str,
        filters: Optional[Any] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        return self.chunks[:num_results]

    def get_chunks_by_document(
        self,
        document_id: str,
        chunk_range: Optional[tuple[int, int]] = None,
    ) -> list[Chunk]:
        return [c for c in self.chunks if c.document_id == document_id]

    def get_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> Optional[Chunk]:
        for chunk in self.chunks:
            if chunk.document_id == document_id and chunk.chunk_id == chunk_id:
                return chunk
        return None


class MockTool(Tool):
    """Mock tool for testing."""

    NAME = "mock_tool"
    DESCRIPTION = "A mock tool for testing"

    def __init__(self, response: str = "Mock tool response"):
        super().__init__(id=1)
        self.response = response
        self.call_count = 0
        self.last_kwargs: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    def tool_definition(self) -> dict[str, Any]:
        return self.build_tool_definition(
            parameters={
                "query": {"type": "string", "description": "Test query"},
            },
            required=["query"],
        )

    def run(
        self,
        override_kwargs: Optional[Any] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        self.call_count += 1
        self.last_kwargs = llm_kwargs
        return ToolResponse(llm_response=self.response)


@pytest.fixture
def mock_llm():
    """Fixture for mock LLM."""
    return MockLLM()


@pytest.fixture
def mock_document_index():
    """Fixture for mock document index."""
    chunks = [
        Chunk(
            document_id="doc1",
            chunk_id=0,
            content="This is test content about Python programming.",
            title="Python Guide",
            score=0.9,
        ),
        Chunk(
            document_id="doc1",
            chunk_id=1,
            content="More content about Python functions and classes.",
            title="Python Guide",
            score=0.8,
        ),
        Chunk(
            document_id="doc2",
            chunk_id=0,
            content="JavaScript is a web programming language.",
            title="JavaScript Basics",
            score=0.7,
        ),
    ]
    return MockDocumentIndex(chunks)


@pytest.fixture
def mock_tool():
    """Fixture for mock tool."""
    return MockTool()


@pytest.fixture
def sample_chunks():
    """Fixture for sample chunks."""
    return [
        Chunk(
            document_id="doc1",
            chunk_id=0,
            content="Sample content 1",
            title="Document 1",
            score=0.9,
        ),
        Chunk(
            document_id="doc2",
            chunk_id=0,
            content="Sample content 2",
            title="Document 2",
            score=0.8,
        ),
    ]


@pytest.fixture
def sample_messages():
    """Fixture for sample messages."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
    ]
