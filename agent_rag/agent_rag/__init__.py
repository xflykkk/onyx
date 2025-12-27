"""
Agent RAG - A standalone Agent RAG component with Chat and Deep Research capabilities.

This package provides:
- ChatAgent: For conversational RAG with tool calling
- DeepResearchAgent: For multi-step research with parallel execution
- Tools: SearchTool, WebSearchTool, OpenURLTool, and extensible custom tools
- DocumentIndex: Vespa and Memory implementations for vector search
- LLM: LiteLLM-based provider with streaming support
"""

from agent_rag.core.models import (
    Message,
    AgentResponse,
    Chunk,
    Section,
)
from agent_rag.core.config import (
    AgentConfig,
    AgentMode,
    LLMConfig,
    SearchConfig,
    DeepResearchConfig,
)
from agent_rag.agent.chat_agent import ChatAgent
from agent_rag.agent.deep_research.orchestrator import DeepResearchOrchestrator as DeepResearchAgent

__version__ = "0.1.0"

__all__ = [
    # Core models
    "Message",
    "AgentResponse",
    "Chunk",
    "Section",
    # Config
    "AgentConfig",
    "AgentMode",
    "LLMConfig",
    "SearchConfig",
    "DeepResearchConfig",
    # Agents
    "ChatAgent",
    "DeepResearchAgent",
]
