"""Memory-based document index implementation."""

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from agent_rag.core.models import Chunk, SearchFilters
from agent_rag.document_index.interface import DocumentIndex
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def tokenize(text: str) -> list[str]:
    """Simple tokenization for BM25."""
    # Lowercase and split on non-alphanumeric
    tokens = re.findall(r'\w+', text.lower())
    return tokens


class BM25:
    """Simple BM25 implementation for keyword search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.doc_lengths: dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0
        self.doc_tokens: dict[str, dict[str, int]] = {}

    def add_document(self, doc_id: str, text: str) -> None:
        """Add a document to the index."""
        tokens = tokenize(text)
        token_freqs: dict[str, int] = defaultdict(int)

        for token in tokens:
            token_freqs[token] += 1

        # Update document frequencies
        for token in set(tokens):
            self.doc_freqs[token] += 1

        self.doc_tokens[doc_id] = dict(token_freqs)
        self.doc_lengths[doc_id] = len(tokens)
        self.num_docs += 1

        # Recalculate average document length
        self.avg_doc_length = sum(self.doc_lengths.values()) / self.num_docs

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index."""
        if doc_id not in self.doc_tokens:
            return

        token_freqs = self.doc_tokens[doc_id]
        for token in token_freqs:
            self.doc_freqs[token] -= 1
            if self.doc_freqs[token] <= 0:
                del self.doc_freqs[token]

        del self.doc_tokens[doc_id]
        del self.doc_lengths[doc_id]
        self.num_docs -= 1

        if self.num_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.num_docs
        else:
            self.avg_doc_length = 0.0

    def score(self, doc_id: str, query: str) -> float:
        """Calculate BM25 score for a document given a query."""
        if doc_id not in self.doc_tokens:
            return 0.0

        query_tokens = tokenize(query)
        doc_token_freqs = self.doc_tokens[doc_id]
        doc_length = self.doc_lengths[doc_id]

        score = 0.0
        for token in query_tokens:
            if token not in doc_token_freqs:
                continue

            tf = doc_token_freqs[token]
            df = self.doc_freqs.get(token, 0)

            if df == 0:
                continue

            idf = math.log((self.num_docs - df + 0.5) / (df + 0.5) + 1)
            tf_component = tf * (self.k1 + 1) / (
                tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            )
            score += idf * tf_component

        return score


class MemoryIndex(DocumentIndex):
    """In-memory document index for testing and lightweight usage."""

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self.chunks: dict[str, Chunk] = {}  # unique_id -> Chunk
        self.documents: dict[str, list[str]] = defaultdict(list)  # doc_id -> [unique_ids]
        self.bm25 = BM25()
        self.persist_path = persist_path

        if persist_path:
            self._load()

    def _chunk_id(self, document_id: str, chunk_id: int) -> str:
        """Generate unique chunk ID."""
        return f"{document_id}_{chunk_id}"

    def _matches_filters(self, chunk: Chunk, filters: Optional[SearchFilters]) -> bool:
        """Check if chunk matches filters."""
        if filters is None:
            return True

        if filters.source_types and chunk.source_type not in filters.source_types:
            return False

        if filters.document_ids and chunk.document_id not in filters.document_ids:
            return False

        if filters.time_cutoff and chunk.updated_at:
            if chunk.updated_at < filters.time_cutoff:
                return False

        if filters.tags:
            chunk_tags = chunk.metadata.get("tags", [])
            if not any(tag in chunk_tags for tag in filters.tags):
                return False

        return True

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        filters: Optional[SearchFilters] = None,
        hybrid_alpha: float = 0.5,
        num_results: int = 10,
    ) -> list[Chunk]:
        """Perform hybrid search."""
        # Get semantic scores
        semantic_scores: dict[str, float] = {}
        for uid, chunk in self.chunks.items():
            if not self._matches_filters(chunk, filters):
                continue
            if chunk.embedding:
                semantic_scores[uid] = cosine_similarity(query_embedding, chunk.embedding)

        # Get keyword scores
        keyword_scores: dict[str, float] = {}
        for uid, chunk in self.chunks.items():
            if not self._matches_filters(chunk, filters):
                continue
            keyword_scores[uid] = self.bm25.score(uid, query)

        # Normalize scores
        max_semantic = max(semantic_scores.values()) if semantic_scores else 1.0
        max_keyword = max(keyword_scores.values()) if keyword_scores else 1.0

        if max_semantic > 0:
            semantic_scores = {k: v / max_semantic for k, v in semantic_scores.items()}
        if max_keyword > 0:
            keyword_scores = {k: v / max_keyword for k, v in keyword_scores.items()}

        # Combine scores
        all_uids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        combined_scores: dict[str, float] = {}

        for uid in all_uids:
            semantic = semantic_scores.get(uid, 0.0)
            keyword = keyword_scores.get(uid, 0.0)
            combined_scores[uid] = hybrid_alpha * semantic + (1 - hybrid_alpha) * keyword

        # Sort and return top results
        sorted_uids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)
        results: list[Chunk] = []

        for uid in sorted_uids[:num_results]:
            chunk = self.chunks[uid]
            chunk.score = combined_scores[uid]
            results.append(chunk)

        return results

    def semantic_search(
        self,
        query_embedding: list[float],
        filters: Optional[SearchFilters] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        """Perform semantic search."""
        scores: list[tuple[str, float]] = []

        for uid, chunk in self.chunks.items():
            if not self._matches_filters(chunk, filters):
                continue
            if chunk.embedding:
                score = cosine_similarity(query_embedding, chunk.embedding)
                scores.append((uid, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        results: list[Chunk] = []

        for uid, score in scores[:num_results]:
            chunk = self.chunks[uid]
            chunk.score = score
            results.append(chunk)

        return results

    def keyword_search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        num_results: int = 10,
    ) -> list[Chunk]:
        """Perform keyword search."""
        scores: list[tuple[str, float]] = []

        for uid, chunk in self.chunks.items():
            if not self._matches_filters(chunk, filters):
                continue
            score = self.bm25.score(uid, query)
            if score > 0:
                scores.append((uid, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        results: list[Chunk] = []

        for uid, score in scores[:num_results]:
            chunk = self.chunks[uid]
            chunk.score = score
            results.append(chunk)

        return results

    def get_chunks_by_document(
        self,
        document_id: str,
        chunk_range: Optional[tuple[int, int]] = None,
    ) -> list[Chunk]:
        """Get chunks for a document."""
        if document_id not in self.documents:
            return []

        chunks: list[Chunk] = []
        for uid in self.documents[document_id]:
            chunk = self.chunks.get(uid)
            if chunk:
                if chunk_range:
                    start, end = chunk_range
                    if start <= chunk.chunk_id < end:
                        chunks.append(chunk)
                else:
                    chunks.append(chunk)

        chunks.sort(key=lambda x: x.chunk_id)
        return chunks

    def get_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> Optional[Chunk]:
        """Get a specific chunk."""
        uid = self._chunk_id(document_id, chunk_id)
        return self.chunks.get(uid)

    def index_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[str]:
        """Index chunks."""
        indexed_ids: list[str] = []

        for chunk in chunks:
            uid = self._chunk_id(chunk.document_id, chunk.chunk_id)

            # Remove old version if exists
            if uid in self.chunks:
                self.bm25.remove_document(uid)

            self.chunks[uid] = chunk
            self.documents[chunk.document_id].append(uid)
            self.bm25.add_document(uid, chunk.content)
            indexed_ids.append(uid)

        if self.persist_path:
            self._save()

        return indexed_ids

    def delete_document(
        self,
        document_id: str,
    ) -> bool:
        """Delete a document."""
        if document_id not in self.documents:
            return False

        for uid in self.documents[document_id]:
            if uid in self.chunks:
                del self.chunks[uid]
                self.bm25.remove_document(uid)

        del self.documents[document_id]

        if self.persist_path:
            self._save()

        return True

    def delete_chunk(
        self,
        document_id: str,
        chunk_id: int,
    ) -> bool:
        """Delete a specific chunk."""
        uid = self._chunk_id(document_id, chunk_id)

        if uid not in self.chunks:
            return False

        del self.chunks[uid]
        self.bm25.remove_document(uid)

        if document_id in self.documents:
            self.documents[document_id] = [
                u for u in self.documents[document_id] if u != uid
            ]

        if self.persist_path:
            self._save()

        return True

    def _save(self) -> None:
        """Save index to disk."""
        if not self.persist_path:
            return

        path = Path(self.persist_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "chunks": {
                uid: {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "embedding": chunk.embedding,
                    "title": chunk.title,
                    "source_type": chunk.source_type,
                    "link": chunk.link,
                    "metadata": chunk.metadata,
                }
                for uid, chunk in self.chunks.items()
            },
        }

        with open(path, "w") as f:
            json.dump(data, f)

    def _load(self) -> None:
        """Load index from disk."""
        if not self.persist_path:
            return

        path = Path(self.persist_path)
        if not path.exists():
            return

        try:
            with open(path) as f:
                data = json.load(f)

            for uid, chunk_data in data.get("chunks", {}).items():
                chunk = Chunk(
                    document_id=chunk_data["document_id"],
                    chunk_id=chunk_data["chunk_id"],
                    content=chunk_data["content"],
                    embedding=chunk_data.get("embedding"),
                    title=chunk_data.get("title"),
                    source_type=chunk_data.get("source_type"),
                    link=chunk_data.get("link"),
                    metadata=chunk_data.get("metadata", {}),
                )
                self.chunks[uid] = chunk
                self.documents[chunk.document_id].append(uid)
                self.bm25.add_document(uid, chunk.content)

            logger.info(f"Loaded {len(self.chunks)} chunks from {path}")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
