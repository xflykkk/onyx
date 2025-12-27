"""Document index module for Agent RAG."""

from agent_rag.document_index.interface import DocumentIndex
from agent_rag.document_index.memory.memory_index import MemoryIndex

__all__ = [
    "DocumentIndex",
    "MemoryIndex",
]

# Optional Vespa import
try:
    from agent_rag.document_index.vespa.vespa_index import VespaIndex
    __all__.append("VespaIndex")
except ImportError:
    pass
