"""Vespa-based document index implementation."""

from typing import Any, Optional

import httpx

from agent_rag.core.config import DocumentIndexConfig
from agent_rag.core.exceptions import DocumentIndexError
from agent_rag.core.models import Chunk, SearchFilters
from agent_rag.document_index.interface import DocumentIndex
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


class VespaIndex(DocumentIndex):
    """Vespa-based document index for production use."""

    def __init__(
        self,
        config: Optional[DocumentIndexConfig] = None,
        host: str = "localhost",
        port: int = 8080,
        app_name: str = "agent_rag",
        timeout: int = 30,
    ) -> None:
        if config:
            self.host = config.vespa_host
            self.port = config.vespa_port
            self.app_name = config.vespa_app_name
            self.timeout = config.vespa_timeout
        else:
            self.host = host
            self.port = port
            self.app_name = app_name
            self.timeout = timeout

        self.base_url = f"http://{self.host}:{self.port}"
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    def _build_yql_query(
        self,
        query: Optional[str] = None,
        query_embedding: Optional[list[float]] = None,
        filters: Optional[SearchFilters] = None,
        hybrid_alpha: float = 0.5,
        num_results: int = 10,
    ) -> dict[str, Any]:
        """Build Vespa YQL query."""
        # Build filter conditions
        conditions = []

        if filters:
            if filters.source_types:
                source_filter = " OR ".join(
                    f'source_type contains "{st}"' for st in filters.source_types
                )
                conditions.append(f"({source_filter})")

            if filters.document_ids:
                doc_filter = " OR ".join(
                    f'document_id contains "{did}"' for did in filters.document_ids
                )
                conditions.append(f"({doc_filter})")

        where_clause = " AND ".join(conditions) if conditions else "true"

        # Build YQL
        yql_parts = [f"select * from chunk where {where_clause}"]

        if query:
            yql_parts.append(f'and userQuery("{query}")')

        yql = " ".join(yql_parts)

        # Build request body
        body: dict[str, Any] = {
            "yql": yql,
            "hits": num_results,
            "ranking": "hybrid" if query_embedding else "bm25",
        }

        if query_embedding:
            body["ranking.features.query(embedding)"] = query_embedding
            body["ranking.properties.hybrid_alpha"] = hybrid_alpha

        if query:
            body["query"] = query

        return body

    def _parse_vespa_hit(self, hit: dict[str, Any]) -> Chunk:
        """Parse Vespa hit to Chunk."""
        fields = hit.get("fields", {})

        return Chunk(
            document_id=fields.get("document_id", ""),
            chunk_id=int(fields.get("chunk_id", 0)),
            content=fields.get("content", ""),
            embedding=fields.get("embedding"),
            title=fields.get("title"),
            source_type=fields.get("source_type"),
            link=fields.get("link"),
            metadata=fields.get("metadata", {}),
            score=hit.get("relevance", 0.0),
        )

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        filters: Optional[SearchFilters] = None,
        hybrid_alpha: float = 0.5,
        num_results: int = 10,
    ) -> list[Chunk]:
        """Perform hybrid search."""
        body = self._build_yql_query(
            query=query,
            query_embedding=query_embedding,
            filters=filters,
            hybrid_alpha=hybrid_alpha,
            num_results=num_results,
        )

        try:
            response = self.client.post("/search/", json=body)
            response.raise_for_status()
            data = response.json()

            hits = data.get("root", {}).get("children", [])
            return [self._parse_vespa_hit(hit) for hit in hits]
        except httpx.HTTPError as e:
            raise DocumentIndexError(
                f"Vespa search failed: {e}",
                index_type="vespa",
            )

    def semantic_search(
        self,
        query_embedding: list[float],
        filters: Optional[SearchFilters] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        """Perform semantic search."""
        body = self._build_yql_query(
            query_embedding=query_embedding,
            filters=filters,
            hybrid_alpha=1.0,  # Pure semantic
            num_results=num_results,
        )

        try:
            response = self.client.post("/search/", json=body)
            response.raise_for_status()
            data = response.json()

            hits = data.get("root", {}).get("children", [])
            return [self._parse_vespa_hit(hit) for hit in hits]
        except httpx.HTTPError as e:
            raise DocumentIndexError(
                f"Vespa semantic search failed: {e}",
                index_type="vespa",
            )

    def keyword_search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        """Perform keyword search."""
        body = self._build_yql_query(
            query=query,
            filters=filters,
            hybrid_alpha=0.0,  # Pure keyword
            num_results=num_results,
        )

        try:
            response = self.client.post("/search/", json=body)
            response.raise_for_status()
            data = response.json()

            hits = data.get("root", {}).get("children", [])
            return [self._parse_vespa_hit(hit) for hit in hits]
        except httpx.HTTPError as e:
            raise DocumentIndexError(
                f"Vespa keyword search failed: {e}",
                index_type="vespa",
            )

    def get_chunks_by_document(
        self,
        document_id: str,
        chunk_range: Optional[tuple[int, int]] = None,
    ) -> list[Chunk]:
        """Get chunks for a document."""
        yql = f'select * from chunk where document_id contains "{document_id}"'

        if chunk_range:
            start, end = chunk_range
            yql += f" and chunk_id >= {start} and chunk_id < {end}"

        yql += " order by chunk_id asc"

        body = {"yql": yql, "hits": 1000}

        try:
            response = self.client.post("/search/", json=body)
            response.raise_for_status()
            data = response.json()

            hits = data.get("root", {}).get("children", [])
            return [self._parse_vespa_hit(hit) for hit in hits]
        except httpx.HTTPError as e:
            raise DocumentIndexError(
                f"Vespa get chunks failed: {e}",
                index_type="vespa",
            )

    def get_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> Optional[Chunk]:
        """Get a specific chunk."""
        doc_id = f"{document_id}_{chunk_id}"

        try:
            response = self.client.get(f"/document/v1/chunk/chunk/docid/{doc_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

            fields = data.get("fields", {})
            return Chunk(
                document_id=fields.get("document_id", ""),
                chunk_id=int(fields.get("chunk_id", 0)),
                content=fields.get("content", ""),
                embedding=fields.get("embedding"),
                title=fields.get("title"),
                source_type=fields.get("source_type"),
                link=fields.get("link"),
                metadata=fields.get("metadata", {}),
            )
        except httpx.HTTPError as e:
            raise DocumentIndexError(
                f"Vespa get chunk failed: {e}",
                index_type="vespa",
            )

    def index_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[str]:
        """Index chunks."""
        indexed_ids: list[str] = []

        for chunk in chunks:
            doc_id = f"{chunk.document_id}_{chunk.chunk_id}"

            fields = {
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "title": chunk.title,
                "source_type": chunk.source_type,
                "link": chunk.link,
                "metadata": chunk.metadata,
            }

            if chunk.embedding:
                fields["embedding"] = {"values": chunk.embedding}

            try:
                response = self.client.post(
                    f"/document/v1/chunk/chunk/docid/{doc_id}",
                    json={"fields": fields},
                )
                response.raise_for_status()
                indexed_ids.append(doc_id)
            except httpx.HTTPError as e:
                logger.error(f"Failed to index chunk {doc_id}: {e}")

        return indexed_ids

    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        """Delete a document."""
        # First get all chunks for this document
        chunks = self.get_chunks_by_document(document_id)

        for chunk in chunks:
            self.delete_chunk(document_id, chunk.chunk_id)

        return True

    def delete_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> bool:
        """Delete a specific chunk."""
        doc_id = f"{document_id}_{chunk_id}"

        try:
            response = self.client.delete(f"/document/v1/chunk/chunk/docid/{doc_id}")
            return response.status_code == 200
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete chunk {doc_id}: {e}")
            return False

    def close(self) -> None:
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None
