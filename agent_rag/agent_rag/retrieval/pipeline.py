"""Retrieval pipeline for Agent RAG."""

from dataclasses import dataclass, field
from typing import Optional

from agent_rag.core.config import SearchConfig
from agent_rag.core.models import Chunk, SearchFilters, Section
from agent_rag.document_index.interface import DocumentIndex
from agent_rag.embedding.interface import Embedder
from agent_rag.retrieval.ranking import reciprocal_rank_fusion
from agent_rag.utils.concurrency import run_in_parallel
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Result from retrieval pipeline."""
    chunks: list[Chunk]
    sections: list[Section] = field(default_factory=list)
    queries_used: list[str] = field(default_factory=list)
    total_hits: int = 0


class RetrievalPipeline:
    """Pipeline for document retrieval."""

    def __init__(
        self,
        document_index: DocumentIndex,
        embedder: Embedder,
        config: Optional[SearchConfig] = None,
    ) -> None:
        self.document_index = document_index
        self.embedder = embedder
        self.config = config or SearchConfig()

    def retrieve(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        num_results: Optional[int] = None,
        expanded_queries: Optional[list[str]] = None,
    ) -> RetrievalResult:
        """
        Retrieve documents for a query.

        Args:
            query: Main query
            filters: Optional filters
            num_results: Number of results (defaults to config)
            expanded_queries: Optional expanded queries

        Returns:
            Retrieval result with chunks and sections
        """
        num_results = num_results or self.config.num_results

        # Collect all queries
        all_queries = [query]
        if expanded_queries:
            all_queries.extend(expanded_queries)

        # Generate embeddings for all queries
        embeddings = self.embedder.embed_batch(all_queries)

        # Run searches in parallel for each query
        def run_search(q: str, emb: list[float]) -> list[Chunk]:
            return self.document_index.hybrid_search(
                query=q,
                query_embedding=emb,
                filters=filters,
                hybrid_alpha=self.config.default_hybrid_alpha,
                num_results=num_results * 2,  # Get more for RRF
            )

        search_tasks = [
            (run_search, (q, emb))
            for q, emb in zip(all_queries, embeddings)
        ]

        search_results = run_in_parallel(search_tasks, allow_failures=True)

        # Filter out None results
        all_chunk_lists: list[list[Chunk]] = []
        for result in search_results:
            if result:
                all_chunk_lists.append(result)

        if not all_chunk_lists:
            return RetrievalResult(
                chunks=[],
                queries_used=all_queries,
                total_hits=0,
            )

        # Merge results using RRF
        merged_chunks = reciprocal_rank_fusion(
            chunk_lists=all_chunk_lists,
            k=60,
        )

        # Take top results
        top_chunks = merged_chunks[:num_results]

        # Expand to sections if enabled
        sections: list[Section] = []
        if self.config.enable_context_expansion:
            sections = self._expand_to_sections(top_chunks)

        return RetrievalResult(
            chunks=top_chunks,
            sections=sections,
            queries_used=all_queries,
            total_hits=len(merged_chunks),
        )

    def _expand_to_sections(
        self,
        chunks: list[Chunk],
    ) -> list[Section]:
        """Expand chunks to sections with surrounding context."""
        sections: list[Section] = []
        seen_ranges: set[tuple[str, int, int]] = set()

        expand_before = self.config.context_expansion_chunks
        expand_after = self.config.context_expansion_chunks

        for chunk in chunks:
            # Calculate range
            start = max(0, chunk.chunk_id - expand_before)
            end = chunk.chunk_id + expand_after + 1

            # Check if we've already seen this range
            range_key = (chunk.document_id, start, end)
            if range_key in seen_ranges:
                continue
            seen_ranges.add(range_key)

            # Get section
            section = self.document_index.get_section(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                expand_before=expand_before,
                expand_after=expand_after,
            )

            if section:
                sections.append(section)

        return sections

    def deduplicate_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """Remove duplicate chunks, keeping highest scoring."""
        seen: dict[str, Chunk] = {}

        for chunk in chunks:
            key = chunk.unique_id
            if key not in seen or chunk.score > seen[key].score:
                seen[key] = chunk

        return list(seen.values())

    def merge_adjacent_chunks(
        self,
        chunks: list[Chunk],
        max_gap: int = 1,
    ) -> list[Section]:
        """Merge adjacent chunks from the same document into sections."""
        if not chunks:
            return []

        # Sort by document and chunk ID
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (c.document_id, c.chunk_id),
        )

        sections: list[Section] = []
        current_section_chunks: list[Chunk] = [sorted_chunks[0]]

        for chunk in sorted_chunks[1:]:
            last_chunk = current_section_chunks[-1]

            # Check if adjacent (within max_gap)
            if (
                chunk.document_id == last_chunk.document_id
                and chunk.chunk_id <= last_chunk.chunk_id + max_gap + 1
            ):
                current_section_chunks.append(chunk)
            else:
                # Create section from current chunks
                sections.append(self._create_section(current_section_chunks))
                current_section_chunks = [chunk]

        # Don't forget the last section
        if current_section_chunks:
            sections.append(self._create_section(current_section_chunks))

        return sections

    def _create_section(self, chunks: list[Chunk]) -> Section:
        """Create a section from chunks."""
        # Sort by chunk ID
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_id)

        # Find center chunk (highest scoring)
        center_chunk = max(chunks, key=lambda c: c.score)

        # Combine content
        combined_content = "\n\n".join(c.content for c in sorted_chunks)

        return Section(
            center_chunk=center_chunk,
            chunks=sorted_chunks,
            combined_content=combined_content,
        )
