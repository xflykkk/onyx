"""Ranking algorithms for Agent RAG."""

from collections import defaultdict
from typing import Optional

from agent_rag.core.models import Chunk


def reciprocal_rank_fusion(
    chunk_lists: list[list[Chunk]],
    k: int = 60,
    weights: Optional[list[float]] = None,
) -> list[Chunk]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF formula: score(d) = sum(1 / (k + rank(d)))

    Args:
        chunk_lists: List of ranked chunk lists
        k: Constant to prevent division by zero and control influence of high ranks
        weights: Optional weights for each list

    Returns:
        Merged and re-ranked list of chunks
    """
    if not chunk_lists:
        return []

    if weights is None:
        weights = [1.0] * len(chunk_lists)

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Calculate RRF scores
    rrf_scores: dict[str, float] = defaultdict(float)
    chunk_map: dict[str, Chunk] = {}

    for list_idx, chunk_list in enumerate(chunk_lists):
        weight = weights[list_idx]
        for rank, chunk in enumerate(chunk_list):
            unique_id = chunk.unique_id
            rrf_scores[unique_id] += weight * (1.0 / (k + rank + 1))

            # Keep the chunk with highest original score
            if unique_id not in chunk_map or chunk.score > chunk_map[unique_id].score:
                chunk_map[unique_id] = chunk

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    # Build result with updated scores
    result: list[Chunk] = []
    for unique_id in sorted_ids:
        chunk = chunk_map[unique_id]
        chunk.score = rrf_scores[unique_id]
        result.append(chunk)

    return result


def linear_combination(
    chunk_lists: list[list[Chunk]],
    weights: Optional[list[float]] = None,
    normalize: bool = True,
) -> list[Chunk]:
    """
    Merge multiple ranked lists using linear combination of scores.

    Args:
        chunk_lists: List of ranked chunk lists
        weights: Optional weights for each list
        normalize: Whether to normalize scores to [0, 1]

    Returns:
        Merged and re-ranked list of chunks
    """
    if not chunk_lists:
        return []

    if weights is None:
        weights = [1.0] * len(chunk_lists)

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Normalize scores within each list if requested
    if normalize:
        normalized_lists: list[list[Chunk]] = []
        for chunk_list in chunk_lists:
            if not chunk_list:
                normalized_lists.append([])
                continue

            max_score = max(c.score for c in chunk_list)
            min_score = min(c.score for c in chunk_list)
            score_range = max_score - min_score

            if score_range > 0:
                for chunk in chunk_list:
                    chunk.score = (chunk.score - min_score) / score_range
            normalized_lists.append(chunk_list)
        chunk_lists = normalized_lists

    # Combine scores
    combined_scores: dict[str, float] = defaultdict(float)
    chunk_map: dict[str, Chunk] = {}

    for list_idx, chunk_list in enumerate(chunk_lists):
        weight = weights[list_idx]
        for chunk in chunk_list:
            unique_id = chunk.unique_id
            combined_scores[unique_id] += weight * chunk.score

            if unique_id not in chunk_map:
                chunk_map[unique_id] = chunk

    # Sort by combined score
    sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)

    # Build result
    result: list[Chunk] = []
    for unique_id in sorted_ids:
        chunk = chunk_map[unique_id]
        chunk.score = combined_scores[unique_id]
        result.append(chunk)

    return result


def rerank_by_relevance(
    chunks: list[Chunk],
    query: str,
    top_k: Optional[int] = None,
) -> list[Chunk]:
    """
    Simple relevance-based reranking using keyword matching.

    This is a basic implementation. For production, consider using
    a cross-encoder model like ms-marco-MiniLM.

    Args:
        chunks: Chunks to rerank
        query: Query string
        top_k: Optional number of top results to return

    Returns:
        Reranked chunks
    """
    query_terms = set(query.lower().split())

    def relevance_score(chunk: Chunk) -> float:
        content_lower = chunk.content.lower()
        title_lower = (chunk.title or "").lower()

        # Count matching terms
        content_matches = sum(1 for term in query_terms if term in content_lower)
        title_matches = sum(1 for term in query_terms if term in title_lower)

        # Weight title matches higher
        return content_matches + (title_matches * 2) + chunk.score

    # Sort by relevance score
    sorted_chunks = sorted(chunks, key=relevance_score, reverse=True)

    if top_k:
        return sorted_chunks[:top_k]

    return sorted_chunks
