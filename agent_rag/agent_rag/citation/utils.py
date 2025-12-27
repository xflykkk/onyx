"""Citation utilities for Agent RAG."""

import re
from typing import Optional

from agent_rag.core.models import Citation, Chunk


def format_citation_reference(citation_id: int) -> str:
    """Format a citation reference for display."""
    return f"[{citation_id}]"


def format_citation_list(
    citations: list[Citation],
    include_content: bool = False,
    max_content_length: int = 200,
) -> str:
    """
    Format a list of citations for display.

    Args:
        citations: List of citations to format
        include_content: Whether to include content snippets
        max_content_length: Max length of content snippet

    Returns:
        Formatted citation list as string
    """
    if not citations:
        return ""

    lines = ["## Sources\n"]

    for citation in citations:
        # Build citation line
        line_parts = [f"[{citation.citation_id}]"]

        if citation.title:
            line_parts.append(f" {citation.title}")

        if citation.link:
            line_parts.append(f" - {citation.link}")
        elif citation.source_type:
            line_parts.append(f" ({citation.source_type})")

        lines.append(''.join(line_parts))

        if include_content and citation.content:
            content = citation.content
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            lines.append(f"   > {content}\n")

    return '\n'.join(lines)


def format_citation_for_prompt(
    chunks: list[Chunk],
    include_metadata: bool = True,
) -> str:
    """
    Format chunks as numbered citations for LLM prompt.

    Args:
        chunks: Chunks to format
        include_metadata: Whether to include metadata

    Returns:
        Formatted string for prompt
    """
    if not chunks:
        return "No sources available."

    parts = []

    for i, chunk in enumerate(chunks, 1):
        header_parts = [f"[{i}]"]

        if chunk.title:
            header_parts.append(f" {chunk.title}")

        if chunk.source_type:
            header_parts.append(f" ({chunk.source_type})")

        parts.append(''.join(header_parts))
        parts.append(chunk.content)

        if include_metadata and chunk.metadata:
            meta_items = []
            for key, value in chunk.metadata.items():
                if key not in ('embedding', 'raw_content'):
                    meta_items.append(f"{key}: {value}")
            if meta_items:
                parts.append(f"Metadata: {', '.join(meta_items)}")

        parts.append("")  # Empty line between sources

    return '\n'.join(parts)


def build_citation_instruction() -> str:
    """Build instruction for LLM about how to use citations."""
    return """When using information from the provided sources, cite them using [N] notation where N is the source number.
- Place citations immediately after the relevant information
- Use multiple citations [1][2] when information comes from multiple sources
- Only cite sources that directly support your statements
- If information is not from any source, do not add a citation"""


def extract_citation_context(
    text: str,
    citation_id: int,
    context_chars: int = 100,
) -> list[str]:
    """
    Extract text context around each occurrence of a citation.

    Args:
        text: Text containing citations
        citation_id: Citation ID to find
        context_chars: Characters of context to include

    Returns:
        List of context strings for each occurrence
    """
    pattern = re.compile(rf'\[{citation_id}\]|\[[\d,\s]*{citation_id}[\d,\s]*\]')
    contexts = []

    for match in pattern.finditer(text):
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)

        context = text[start:end]

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."

        contexts.append(context)

    return contexts


def merge_citation_lists(
    *citation_lists: list[Citation],
    deduplicate: bool = True,
) -> list[Citation]:
    """
    Merge multiple citation lists.

    Args:
        *citation_lists: Citation lists to merge
        deduplicate: Whether to remove duplicates by document_id

    Returns:
        Merged citation list with renumbered IDs
    """
    merged: list[Citation] = []
    seen_docs: set[str] = set()

    for citations in citation_lists:
        for citation in citations:
            if deduplicate and citation.document_id in seen_docs:
                continue

            seen_docs.add(citation.document_id)
            merged.append(citation)

    # Renumber
    for i, citation in enumerate(merged, 1):
        citation.citation_id = i

    return merged


def remap_citations_in_text(
    text: str,
    id_mapping: dict[int, int],
) -> str:
    """
    Remap citation IDs in text using a mapping.

    Args:
        text: Text containing citations
        id_mapping: Dict mapping old_id -> new_id

    Returns:
        Text with remapped citations
    """
    pattern = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')

    def replace_match(match: re.Match) -> str:
        refs = match.group(1).split(',')
        new_refs = []

        for ref in refs:
            try:
                old_id = int(ref.strip())
                new_id = id_mapping.get(old_id, old_id)
                new_refs.append(str(new_id))
            except ValueError:
                new_refs.append(ref.strip())

        return f"[{','.join(new_refs)}]"

    return pattern.sub(replace_match, text)


def chunk_to_citation(
    chunk: Chunk,
    citation_id: int,
) -> Citation:
    """Convert a chunk to a citation."""
    return Citation(
        citation_id=citation_id,
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        title=chunk.title,
        link=chunk.link,
        source_type=chunk.source_type,
        metadata=chunk.metadata,
    )


def chunks_to_citations(
    chunks: list[Chunk],
    start_id: int = 1,
) -> list[Citation]:
    """Convert a list of chunks to citations."""
    return [
        chunk_to_citation(chunk, i)
        for i, chunk in enumerate(chunks, start_id)
    ]


def validate_citation_coverage(
    text: str,
    citations: list[Citation],
) -> dict[str, any]:
    """
    Validate how well citations are used in text.

    Args:
        text: Text to validate
        citations: Available citations

    Returns:
        Validation report with stats and issues
    """
    pattern = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')

    used_ids: set[int] = set()
    invalid_ids: list[int] = []

    for match in pattern.finditer(text):
        refs = match.group(1).split(',')
        for ref in refs:
            try:
                citation_id = int(ref.strip())
                used_ids.add(citation_id)

                if citation_id < 1 or citation_id > len(citations):
                    invalid_ids.append(citation_id)
            except ValueError:
                continue

    available_ids = set(range(1, len(citations) + 1))
    unused_ids = available_ids - used_ids

    return {
        "total_citations": len(citations),
        "used_count": len(used_ids),
        "unused_count": len(unused_ids),
        "used_ids": sorted(used_ids),
        "unused_ids": sorted(unused_ids),
        "invalid_ids": invalid_ids,
        "coverage_ratio": len(used_ids) / len(citations) if citations else 0,
    }
