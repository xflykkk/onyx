"""Tests for agent system."""

import pytest
from unittest.mock import MagicMock, patch

from agent_rag.agent.base import BaseAgent, AgentState
from agent_rag.agent.step import AgentStep, StepResult
from agent_rag.agent.chat_agent import ChatAgent
from agent_rag.core.models import Message, ToolCall
from agent_rag.tools.registry import ToolRegistry


class TestAgentState:
    """Tests for AgentState."""

    def test_default_state(self):
        state = AgentState()
        assert state.messages == []
        assert state.tool_calls == []
        assert state.step_count == 0
        assert state.should_stop is False

    def test_state_with_messages(self):
        messages = [Message(role="user", content="Hello")]
        state = AgentState(messages=messages)
        assert len(state.messages) == 1


class TestAgentStep:
    """Tests for AgentStep."""

    def test_step_result_creation(self):
        result = StepResult(
            content="Test response",
            tool_calls=[],
            should_continue=False,
            tokens_used=100,
        )
        assert result.content == "Test response"
        assert result.should_continue is False

    def test_step_result_with_tool_calls(self):
        tool_calls = [
            ToolCall(id="tc1", name="search", arguments='{"query": "test"}')
        ]
        result = StepResult(
            content="",
            tool_calls=tool_calls,
            should_continue=True,
        )
        assert len(result.tool_calls) == 1
        assert result.should_continue is True


class TestChatAgent:
    """Tests for ChatAgent."""

    def test_agent_initialization(self, mock_llm):
        agent = ChatAgent(llm=mock_llm)
        assert agent.llm == mock_llm
        assert agent.tool_registry is not None

    def test_agent_reset(self, mock_llm):
        agent = ChatAgent(llm=mock_llm)
        agent.add_user_message("Hello")
        assert len(agent.state.messages) == 1

        agent.reset()
        assert len(agent.state.messages) == 0

    def test_add_messages(self, mock_llm):
        agent = ChatAgent(llm=mock_llm)

        agent.add_system_message("System prompt")
        agent.add_user_message("User message")
        agent.add_assistant_message("Assistant response")

        assert len(agent.state.messages) == 3
        assert agent.state.messages[0].role == "system"
        assert agent.state.messages[1].role == "user"
        assert agent.state.messages[2].role == "assistant"

    def test_should_continue_respects_max_steps(self, mock_llm):
        from agent_rag.core.config import AgentConfig

        config = AgentConfig(max_steps=2)
        agent = ChatAgent(llm=mock_llm, config=config)

        assert agent.should_continue() is True

        agent.state.step_count = 2
        assert agent.should_continue() is False

    def test_should_continue_respects_should_stop(self, mock_llm):
        agent = ChatAgent(llm=mock_llm)
        assert agent.should_continue() is True

        agent.state.should_stop = True
        assert agent.should_continue() is False

    def test_get_tool_definitions(self, mock_llm, mock_tool):
        registry = ToolRegistry()
        registry.register(mock_tool)

        agent = ChatAgent(llm=mock_llm, tool_registry=registry)
        definitions = agent.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "mock_tool"


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_tool(self, mock_tool):
        registry = ToolRegistry()
        registry.register(mock_tool)

        assert registry.get("mock_tool") == mock_tool

    def test_get_nonexistent_tool(self):
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_get_all_definitions(self, mock_tool):
        registry = ToolRegistry()
        registry.register(mock_tool)

        definitions = registry.get_all_definitions()
        assert len(definitions) == 1
        assert definitions[0]["type"] == "function"

    def test_list_tools(self, mock_tool):
        registry = ToolRegistry()
        registry.register(mock_tool)

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0] == "mock_tool"


class TestDeepResearchComponents:
    """Tests for Deep Research components."""

    def test_think_result_structure(self):
        from agent_rag.agent.deep_research.think_tool import ThinkResult

        result = ThinkResult(
            analysis="Test analysis",
            refined_queries=["Query 1", "Query 2"],
            knowledge_gaps=["Gap 1"],
            has_sufficient_info=False,
            confidence=0.7,
        )

        assert result.analysis == "Test analysis"
        assert len(result.refined_queries) == 2
        assert result.confidence == 0.7

    def test_research_findings_structure(self):
        from agent_rag.agent.deep_research.research_agent import ResearchFindings

        findings = ResearchFindings(
            sub_question="What is X?",
            summary="X is...",
            key_facts=["Fact 1", "Fact 2"],
            sources=[],
            confidence=0.8,
            search_queries_used=["query 1"],
        )

        assert findings.sub_question == "What is X?"
        assert findings.confidence == 0.8

    def test_research_report_structure(self):
        from agent_rag.agent.deep_research.report_generator import ResearchReport

        report = ResearchReport(
            title="Test Report",
            summary="Summary here",
            full_report="Full content",
            citations=[],
            key_findings=["Finding 1"],
            limitations=["Limitation 1"],
            confidence=0.75,
        )

        assert report.title == "Test Report"
        assert len(report.key_findings) == 1

    def test_orchestrator_state_enum(self):
        from agent_rag.agent.deep_research.orchestrator import OrchestratorState

        assert OrchestratorState.IDLE.value == "idle"
        assert OrchestratorState.RESEARCHING.value == "researching"
        assert OrchestratorState.COMPLETE.value == "complete"
