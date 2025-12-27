"""Configuration classes for Agent RAG."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class AgentMode(str, Enum):
    """Agent operation mode."""
    CHAT = "chat"
    DEEP_RESEARCH = "deep_research"


class ToolChoice(str, Enum):
    """Tool choice options for LLM."""
    AUTO = "auto"
    REQUIRED = "required"
    NONE = "none"


@dataclass
class LLMConfig:
    """LLM configuration."""
    model: str
    provider: str = "litellm"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4096
    max_input_tokens: int = 128000
    temperature: float = 0.0
    timeout: int = 120

    # Reasoning model configuration
    is_reasoning_model: bool = False
    reasoning_effort: str = "medium"  # low, medium, high

    # Additional provider-specific options
    extra_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model: str = "text-embedding-3-small"
    provider: str = "litellm"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    dimension: int = 1536
    batch_size: int = 32

    # Additional provider-specific options
    extra_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentIndexConfig:
    """Document index configuration."""
    type: str = "memory"  # memory, vespa

    # Vespa configuration
    vespa_host: str = "localhost"
    vespa_port: int = 8080
    vespa_app_name: str = "agent_rag"
    vespa_timeout: int = 30

    # Memory index configuration
    memory_persist_path: Optional[str] = None


@dataclass
class SearchConfig:
    """Search configuration."""
    # Hybrid search
    default_hybrid_alpha: float = 0.5  # 0=keyword only, 1=semantic only
    num_results: int = 10
    max_chunks_per_response: int = 15

    # Query expansion
    enable_query_expansion: bool = True
    max_expanded_queries: int = 3

    # Document selection (LLM-based)
    enable_document_selection: bool = True
    max_documents_to_select: int = 10

    # Context expansion
    enable_context_expansion: bool = True
    context_expansion_chunks: int = 2  # chunks before/after

    # Re-ranking
    enable_reranking: bool = False
    rerank_model: Optional[str] = None


@dataclass
class DeepResearchConfig:
    """Deep Research specific configuration."""
    max_orchestrator_cycles: int = 8
    max_research_cycles: int = 3
    max_research_agents: int = 5

    # Clarification
    skip_clarification: bool = False

    # Think tool for non-reasoning models
    enable_think_tool: bool = True

    # Report generation
    max_intermediate_report_tokens: int = 10000
    max_final_report_tokens: int = 20000


@dataclass
class AgentConfig:
    """Main agent configuration."""
    # Mode
    mode: AgentMode = AgentMode.CHAT

    # System prompt
    system_prompt: Optional[str] = None

    # Chat mode configuration
    max_cycles: int = 6

    # Tool configuration
    enabled_tools: list[str] = field(default_factory=lambda: [
        "internal_search", "web_search", "open_url"
    ])

    # Citation configuration
    enable_citations: bool = True

    # Deep Research configuration
    deep_research: DeepResearchConfig = field(default_factory=DeepResearchConfig)

    # Search configuration
    search: SearchConfig = field(default_factory=SearchConfig)

    # Callbacks (set at runtime)
    on_token: Optional[Callable[[str], None]] = None
    on_tool_start: Optional[Callable[[str, dict[str, Any]], None]] = None
    on_tool_end: Optional[Callable[[str, Any], None]] = None
    on_reasoning: Optional[Callable[[str], None]] = None
    on_research_plan: Optional[Callable[[str], None]] = None
    on_intermediate_report: Optional[Callable[[int, str], None]] = None


@dataclass
class AgentRAGConfig:
    """Complete Agent RAG configuration."""
    llm: LLMConfig
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    document_index: DocumentIndexConfig = field(default_factory=DocumentIndexConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentRAGConfig":
        """Create configuration from dictionary."""
        llm_config = LLMConfig(**data.get("llm", {}))
        embedding_config = EmbeddingConfig(**data.get("embedding", {}))
        index_config = DocumentIndexConfig(**data.get("document_index", {}))

        agent_data = data.get("agent", {})
        if "deep_research" in agent_data:
            agent_data["deep_research"] = DeepResearchConfig(
                **agent_data["deep_research"]
            )
        if "search" in agent_data:
            agent_data["search"] = SearchConfig(**agent_data["search"])
        agent_config = AgentConfig(**agent_data)

        return cls(
            llm=llm_config,
            embedding=embedding_config,
            document_index=index_config,
            agent=agent_config,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        from dataclasses import asdict
        return {
            "llm": asdict(self.llm),
            "embedding": asdict(self.embedding),
            "document_index": asdict(self.document_index),
            "agent": {
                "mode": self.agent.mode.value,
                "system_prompt": self.agent.system_prompt,
                "max_cycles": self.agent.max_cycles,
                "enabled_tools": self.agent.enabled_tools,
                "enable_citations": self.agent.enable_citations,
                "deep_research": asdict(self.agent.deep_research),
                "search": asdict(self.agent.search),
            },
        }
