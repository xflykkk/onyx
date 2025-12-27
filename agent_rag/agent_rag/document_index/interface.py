"""Document index interface definitions."""

from abc import ABC, abstractmethod
from typing import Optional

from agent_rag.core.models import Chunk, SearchFilters, Section


class DocumentIndex(ABC):
    """Abstract base class for document indexes."""

    @abstractmethod
    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        filters: Optional[SearchFilters] = None,
        hybrid_alpha: float = 0.5,
        num_results: int = 10,
    ) -> list[Chunk]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query: Query text for keyword search
            query_embedding: Query embedding for semantic search
            filters: Optional search filters
            hybrid_alpha: Balance between keyword (0) and semantic (1) search
            num_results: Maximum number of results

        Returns:
            List of matching chunks
        """
        pass

    @abstractmethod
    def semantic_search(
        self,
        query_embedding: list[float],
        filters: Optional[SearchFilters] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        """
        Perform semantic search using embeddings.

        Args:
            query_embedding: Query embedding
            filters: Optional search filters
            num_results: Maximum number of results

        Returns:
            List of matching chunks
        """
        pass

    @abstractmethod
    def keyword_search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        """
        Perform keyword search using BM25 or similar.

        Args:
            query: Query text
            filters: Optional search filters
            num_results: Maximum number of results

        Returns:
            List of matching chunks
        """
        pass

    @abstractmethod
    def get_chunks_by_document(
        self,
        document_id: str,
        chunk_range: Optional[tuple[int, int]] = None,
    ) -> list[Chunk]:
        """
        Get chunks for a specific document.

        Args:
            document_id: Document ID
            chunk_range: Optional (start, end) chunk IDs to retrieve

        Returns:
            List of chunks
        """
        pass

    @abstractmethod
    def get_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> Optional[Chunk]:
        """
        Get a specific chunk.

        Args:
            document_id: Document ID
            chunk_id: Chunk ID

        Returns:
            Chunk if found, None otherwise
        """
        pass

    @abstractmethod
    def index_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[str]:
        """
        Index multiple chunks.

        Args:
            chunks: Chunks to index

        Returns:
            List of indexed chunk IDs
        """
        pass

    @abstractmethod
    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    def delete_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> bool:
        """
        Delete a specific chunk.

        Args:
            document_id: Document ID
            chunk_id: Chunk ID

        Returns:
            True if deleted, False otherwise
        """
        pass

    def get_surrounding_chunks(
        self,
        document_id: str,
        chunk_id: int,
        before: int = 2,
        after: int = 2,
    ) -> list[Chunk]:
        """
        Get chunks surrounding a specific chunk.

        Args:
            document_id: Document ID
            chunk_id: Center chunk ID
            before: Number of chunks before
            after: Number of chunks after

        Returns:
            List of surrounding chunks
        """
        start = max(0, chunk_id - before)
        end = chunk_id + after + 1
        return self.get_chunks_by_document(document_id, (start, end))

    def get_section(
        self,
        document_id: str,
        chunk_id: int,
        expand_before: int = 2,
        expand_after: int = 2,
    ) -> Optional[Section]:
        """
        Get a section centered on a chunk.

        Args:
            document_id: Document ID
            chunk_id: Center chunk ID
            expand_before: Chunks to include before
            expand_after: Chunks to include after

        Returns:
            Section if found, None otherwise
        """
        chunks = self.get_surrounding_chunks(
            document_id, chunk_id, expand_before, expand_after
        )

        if not chunks:
            return None

        # Find center chunk
        center_chunk = None
        for chunk in chunks:
            if chunk.chunk_id == chunk_id:
                center_chunk = chunk
                break

        if center_chunk is None:
            return None

        # Combine content
        combined_content = "\n\n".join(chunk.content for chunk in chunks)

        return Section(
            center_chunk=center_chunk,
            chunks=chunks,
            combined_content=combined_content,
        )
