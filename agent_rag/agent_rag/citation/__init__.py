"""Citation system for Agent RAG."""

from agent_rag.citation.processor import (
    CitationExtractor,
    CitationMapping,
    CitationState,
    DynamicCitationProcessor,
)
from agent_rag.citation.utils import (
    build_citation_instruction,
    chunk_to_citation,
    chunks_to_citations,
    extract_citation_context,
    format_citation_for_prompt,
    format_citation_list,
    format_citation_reference,
    merge_citation_lists,
    remap_citations_in_text,
    validate_citation_coverage,
)

__all__ = [
    # Processor
    "DynamicCitationProcessor",
    "CitationExtractor",
    "CitationMapping",
    "CitationState",
    # Utils
    "format_citation_reference",
    "format_citation_list",
    "format_citation_for_prompt",
    "build_citation_instruction",
    "extract_citation_context",
    "merge_citation_lists",
    "remap_citations_in_text",
    "chunk_to_citation",
    "chunks_to_citations",
    "validate_citation_coverage",
]
