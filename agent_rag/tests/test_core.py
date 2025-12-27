"""Tests for core models and configuration."""

import pytest
from agent_rag.core.models import (
    Chunk,
    Citation,
    Message,
    Section,
    ToolCall,
    AgentResponse,
    SearchFilters,
)
from agent_rag.core.config import (
    AgentConfig,
    LLMConfig,
    SearchConfig,
    DeepResearchConfig,
)


class TestChunk:
    """Tests for Chunk model."""

    def test_chunk_creation(self):
        chunk = Chunk(
            document_id="doc1",
            chunk_id=0,
            content="Test content",
        )
        assert chunk.document_id == "doc1"
        assert chunk.chunk_id == 0
        assert chunk.content == "Test content"
        assert chunk.score == 0.0

    def test_chunk_unique_id(self):
        chunk = Chunk(
            document_id="doc1",
            chunk_id=5,
            content="Test",
        )
        assert chunk.unique_id == "doc1_5"

    def test_chunk_with_metadata(self):
        chunk = Chunk(
            document_id="doc1",
            chunk_id=0,
            content="Test",
            title="Test Title",
            source_type="web",
            link="https://example.com",
            metadata={"key": "value"},
        )
        assert chunk.title == "Test Title"
        assert chunk.source_type == "web"
        assert chunk.link == "https://example.com"
        assert chunk.metadata["key"] == "value"


class TestMessage:
    """Tests for Message model."""

    def test_user_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None

    def test_assistant_message_with_tool_calls(self):
        tool_call = ToolCall(
            id="tc1",
            name="search",
            arguments='{"query": "test"}',
        )
        msg = Message(
            role="assistant",
            content="Let me search for that.",
            tool_calls=[tool_call],
        )
        assert msg.role == "assistant"
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "search"

    def test_tool_message(self):
        msg = Message(
            role="tool",
            content="Search results here",
            tool_call_id="tc1",
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "tc1"


class TestToolCall:
    """Tests for ToolCall model."""

    def test_parsed_arguments(self):
        tc = ToolCall(
            id="tc1",
            name="search",
            arguments='{"query": "python", "limit": 10}',
        )
        args = tc.parsed_arguments
        assert args["query"] == "python"
        assert args["limit"] == 10

    def test_parsed_arguments_invalid_json(self):
        tc = ToolCall(
            id="tc1",
            name="search",
            arguments="not valid json",
        )
        args = tc.parsed_arguments
        assert args == {}


class TestCitation:
    """Tests for Citation model."""

    def test_citation_creation(self):
        citation = Citation(
            citation_id=1,
            document_id="doc1",
            chunk_id=0,
            content="Cited content",
        )
        assert citation.citation_id == 1
        assert citation.document_id == "doc1"


class TestSection:
    """Tests for Section model."""

    def test_section_from_chunks(self, sample_chunks):
        section = Section(
            document_id="doc1",
            chunks=sample_chunks,
            combined_content="Combined content here",
        )
        assert section.document_id == "doc1"
        assert len(section.chunks) == 2


class TestSearchFilters:
    """Tests for SearchFilters model."""

    def test_empty_filters(self):
        filters = SearchFilters()
        assert filters.source_types is None
        assert filters.document_ids is None

    def test_with_filters(self):
        filters = SearchFilters(
            source_types=["web", "file"],
            document_ids=["doc1", "doc2"],
        )
        assert len(filters.source_types) == 2
        assert len(filters.document_ids) == 2


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_default_config(self):
        config = AgentConfig()
        assert config.max_steps == 10
        assert config.enable_streaming is True

    def test_custom_config(self):
        config = AgentConfig(
            max_steps=5,
            max_tokens=1000,
            enable_streaming=False,
        )
        assert config.max_steps == 5
        assert config.max_tokens == 1000
        assert config.enable_streaming is False


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_default_config(self):
        config = LLMConfig()
        assert config.model == "gpt-4"
        assert config.temperature == 0.7

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("AGENT_RAG_LLM_MODEL", "claude-3")
        monkeypatch.setenv("AGENT_RAG_LLM_TEMPERATURE", "0.5")
        config = LLMConfig.from_env()
        assert config.model == "claude-3"
        assert config.temperature == 0.5


class TestSearchConfig:
    """Tests for SearchConfig."""

    def test_default_config(self):
        config = SearchConfig()
        assert config.hybrid_alpha == 0.5
        assert config.num_results == 10


class TestDeepResearchConfig:
    """Tests for DeepResearchConfig."""

    def test_default_config(self):
        config = DeepResearchConfig()
        assert config.max_orchestrator_cycles == 8
        assert config.num_research_agents == 3
        assert config.max_agent_cycles == 3
