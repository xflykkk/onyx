"""Vespa-based document index."""

try:
    from agent_rag.document_index.vespa.vespa_index import VespaIndex
    __all__ = ["VespaIndex"]
except ImportError:
    __all__ = []
