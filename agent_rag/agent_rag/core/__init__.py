"""Core module containing models, config, callbacks and exceptions."""

from agent_rag.core.models import (
    Message,
    AgentResponse,
    Chunk,
    Section,
    ToolCall,
    Citation,
)
from agent_rag.core.config import (
    AgentConfig,
    AgentMode,
    LLMConfig,
    EmbeddingConfig,
    SearchConfig,
    DeepResearchConfig,
    DocumentIndexConfig,
)
from agent_rag.core.callbacks import (
    StreamCallback,
    ToolCallback,
    AgentCallback,
)
from agent_rag.core.exceptions import (
    AgentRAGError,
    LLMError,
    ToolError,
    RetrievalError,
    ConfigurationError,
)

__all__ = [
    # Models
    "Message",
    "AgentResponse",
    "Chunk",
    "Section",
    "ToolCall",
    "Citation",
    # Config
    "AgentConfig",
    "AgentMode",
    "LLMConfig",
    "EmbeddingConfig",
    "SearchConfig",
    "DeepResearchConfig",
    "DocumentIndexConfig",
    # Callbacks
    "StreamCallback",
    "ToolCallback",
    "AgentCallback",
    # Exceptions
    "AgentRAGError",
    "LLMError",
    "ToolError",
    "RetrievalError",
    "ConfigurationError",
]
