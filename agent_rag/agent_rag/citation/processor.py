"""Citation processor for Agent RAG.

Handles dynamic citation tracking, mapping, and folding during LLM response generation.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from agent_rag.core.models import Chunk, Citation, Section
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CitationMapping:
    """Maps original citation IDs to display IDs."""
    original_id: str
    display_id: int
    chunk: Chunk
    section: Optional[Section] = None


@dataclass
class CitationState:
    """State for citation processing during streaming."""
    citation_mappings: dict[str, CitationMapping] = field(default_factory=dict)
    next_display_id: int = 1
    pending_text: str = ""


class DynamicCitationProcessor:
    """
    Process citations dynamically during LLM response streaming.

    Supports:
    - Dynamic citation ID assignment as they appear
    - Citation folding (multiple sources to same document)
    - Real-time citation extraction during streaming
    - Final citation list generation
    """

    # Citation pattern: matches [1], [2], [1,2], [1][2], etc.
    CITATION_PATTERN = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')

    def __init__(
        self,
        chunks: list[Chunk],
        sections: Optional[list[Section]] = None,
        fold_citations: bool = True,
    ) -> None:
        """
        Initialize the citation processor.

        Args:
            chunks: Available chunks that can be cited
            sections: Optional sections (merged chunks)
            fold_citations: Whether to fold citations to same document
        """
        self.chunks = chunks
        self.sections = sections or []
        self.fold_citations = fold_citations

        # Build chunk lookup by various IDs
        self._chunk_by_unique_id: dict[str, Chunk] = {
            chunk.unique_id: chunk for chunk in chunks
        }
        self._chunk_by_index: dict[int, Chunk] = {
            i: chunk for i, chunk in enumerate(chunks, 1)
        }

        # For citation folding - group by document
        self._doc_first_chunk: dict[str, Chunk] = {}
        for chunk in chunks:
            if chunk.document_id not in self._doc_first_chunk:
                self._doc_first_chunk[chunk.document_id] = chunk

        # State
        self.state = CitationState()

    def reset(self) -> None:
        """Reset the processor state."""
        self.state = CitationState()

    def _get_or_create_mapping(
        self,
        original_id: str,
    ) -> Optional[CitationMapping]:
        """Get or create a citation mapping for the given original ID."""
        if original_id in self.state.citation_mappings:
            return self.state.citation_mappings[original_id]

        # Try to find the referenced chunk
        chunk: Optional[Chunk] = None

        # Try as numeric index first
        try:
            idx = int(original_id)
            chunk = self._chunk_by_index.get(idx)
        except ValueError:
            # Try as unique ID
            chunk = self._chunk_by_unique_id.get(original_id)

        if not chunk:
            logger.warning(f"Citation reference not found: {original_id}")
            return None

        # For folding, check if we already have a citation for this document
        if self.fold_citations:
            for mapping in self.state.citation_mappings.values():
                if mapping.chunk.document_id == chunk.document_id:
                    # Reuse existing display ID for same document
                    new_mapping = CitationMapping(
                        original_id=original_id,
                        display_id=mapping.display_id,
                        chunk=chunk,
                    )
                    self.state.citation_mappings[original_id] = new_mapping
                    return new_mapping

        # Create new mapping
        display_id = self.state.next_display_id
        self.state.next_display_id += 1

        mapping = CitationMapping(
            original_id=original_id,
            display_id=display_id,
            chunk=chunk,
        )
        self.state.citation_mappings[original_id] = mapping

        return mapping

    def process_token(self, token: str) -> str:
        """
        Process a single token during streaming.

        Accumulates text until complete citations can be processed.

        Args:
            token: The incoming token

        Returns:
            Processed text with updated citation IDs (may be buffered)
        """
        self.state.pending_text += token

        # Check if we have complete citations to process
        # Look for closing bracket that might indicate complete citation
        if ']' not in self.state.pending_text:
            return ""

        # Process complete citations
        result = self._process_pending_text()
        return result

    def _process_pending_text(self) -> str:
        """Process pending text and extract/remap citations."""
        text = self.state.pending_text
        result_parts = []
        last_end = 0

        for match in self.CITATION_PATTERN.finditer(text):
            # Add text before citation
            result_parts.append(text[last_end:match.start()])

            # Process citation references
            refs = match.group(1).split(',')
            display_ids = []

            for ref in refs:
                ref = ref.strip()
                mapping = self._get_or_create_mapping(ref)
                if mapping:
                    display_ids.append(str(mapping.display_id))

            if display_ids:
                result_parts.append(f"[{','.join(display_ids)}]")

            last_end = match.end()

        # Check if there might be an incomplete citation at the end
        remaining = text[last_end:]
        if '[' in remaining and ']' not in remaining[remaining.rfind('['):]:
            # Keep incomplete citation in pending
            incomplete_start = remaining.rfind('[')
            result_parts.append(remaining[:incomplete_start])
            self.state.pending_text = remaining[incomplete_start:]
        else:
            result_parts.append(remaining)
            self.state.pending_text = ""

        return ''.join(result_parts)

    def process_complete_text(self, text: str) -> str:
        """
        Process complete text (non-streaming mode).

        Args:
            text: Complete text to process

        Returns:
            Text with remapped citation IDs
        """
        self.state.pending_text = text
        result = self._process_pending_text()

        # Flush any remaining pending text
        if self.state.pending_text:
            result += self.state.pending_text
            self.state.pending_text = ""

        return result

    def flush(self) -> str:
        """
        Flush any pending text at the end of streaming.

        Returns:
            Any remaining processed text
        """
        if not self.state.pending_text:
            return ""

        # Process remaining text (even if citations are incomplete)
        remaining = self.state.pending_text
        self.state.pending_text = ""

        # Try to process any complete citations
        result_parts = []
        last_end = 0

        for match in self.CITATION_PATTERN.finditer(remaining):
            result_parts.append(remaining[last_end:match.start()])

            refs = match.group(1).split(',')
            display_ids = []

            for ref in refs:
                ref = ref.strip()
                mapping = self._get_or_create_mapping(ref)
                if mapping:
                    display_ids.append(str(mapping.display_id))

            if display_ids:
                result_parts.append(f"[{','.join(display_ids)}]")

            last_end = match.end()

        result_parts.append(remaining[last_end:])
        return ''.join(result_parts)

    def get_citations(self) -> list[Citation]:
        """
        Get the list of citations in display order.

        Returns:
            List of Citation objects ordered by display ID
        """
        # Get unique display IDs and their first mapping
        display_id_to_mapping: dict[int, CitationMapping] = {}

        for mapping in self.state.citation_mappings.values():
            if mapping.display_id not in display_id_to_mapping:
                display_id_to_mapping[mapping.display_id] = mapping

        # Build citations in order
        citations: list[Citation] = []
        for display_id in sorted(display_id_to_mapping.keys()):
            mapping = display_id_to_mapping[display_id]
            chunk = mapping.chunk

            citation = Citation(
                citation_id=display_id,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                title=chunk.title,
                link=chunk.link,
                source_type=chunk.source_type,
                metadata=chunk.metadata,
            )
            citations.append(citation)

        return citations

    def get_citation_mapping(self) -> dict[int, list[str]]:
        """
        Get mapping from display ID to original references.

        Returns:
            Dict mapping display_id -> list of original IDs that map to it
        """
        mapping: dict[int, list[str]] = {}

        for original_id, citation_mapping in self.state.citation_mappings.items():
            display_id = citation_mapping.display_id
            if display_id not in mapping:
                mapping[display_id] = []
            mapping[display_id].append(original_id)

        return mapping


class CitationExtractor:
    """Extract and validate citations from text."""

    CITATION_PATTERN = re.compile(r'\[(\d+(?:,\s*\d+)*)\]')

    @classmethod
    def extract_citation_ids(cls, text: str) -> list[int]:
        """
        Extract all citation IDs from text.

        Args:
            text: Text containing citations

        Returns:
            List of unique citation IDs in order of appearance
        """
        ids: list[int] = []
        seen: set[int] = set()

        for match in cls.CITATION_PATTERN.finditer(text):
            refs = match.group(1).split(',')
            for ref in refs:
                try:
                    citation_id = int(ref.strip())
                    if citation_id not in seen:
                        ids.append(citation_id)
                        seen.add(citation_id)
                except ValueError:
                    continue

        return ids

    @classmethod
    def validate_citations(
        cls,
        text: str,
        max_citation_id: int,
    ) -> tuple[bool, list[int]]:
        """
        Validate that all citations reference valid IDs.

        Args:
            text: Text containing citations
            max_citation_id: Maximum valid citation ID

        Returns:
            Tuple of (is_valid, invalid_ids)
        """
        ids = cls.extract_citation_ids(text)
        invalid = [id for id in ids if id < 1 or id > max_citation_id]
        return len(invalid) == 0, invalid

    @classmethod
    def remove_citations(cls, text: str) -> str:
        """
        Remove all citations from text.

        Args:
            text: Text containing citations

        Returns:
            Text with citations removed
        """
        return cls.CITATION_PATTERN.sub('', text)

    @classmethod
    def count_citations(cls, text: str) -> dict[int, int]:
        """
        Count occurrences of each citation ID.

        Args:
            text: Text containing citations

        Returns:
            Dict mapping citation_id -> count
        """
        counts: dict[int, int] = {}

        for match in cls.CITATION_PATTERN.finditer(text):
            refs = match.group(1).split(',')
            for ref in refs:
                try:
                    citation_id = int(ref.strip())
                    counts[citation_id] = counts.get(citation_id, 0) + 1
                except ValueError:
                    continue

        return counts
