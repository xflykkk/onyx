"""Tests for retrieval system."""

import pytest
from agent_rag.core.models import Chunk
from agent_rag.retrieval.ranking import (
    reciprocal_rank_fusion,
    linear_combination,
    rerank_by_relevance,
)


class TestReciprocalRankFusion:
    """Tests for RRF ranking."""

    def test_empty_lists(self):
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_single_list(self):
        chunks = [
            Chunk(document_id="doc1", chunk_id=0, content="A", score=0.9),
            Chunk(document_id="doc2", chunk_id=0, content="B", score=0.8),
        ]
        result = reciprocal_rank_fusion([chunks])
        assert len(result) == 2
        assert result[0].document_id == "doc1"

    def test_merge_two_lists(self):
        list1 = [
            Chunk(document_id="doc1", chunk_id=0, content="A", score=0.9),
            Chunk(document_id="doc2", chunk_id=0, content="B", score=0.8),
        ]
        list2 = [
            Chunk(document_id="doc2", chunk_id=0, content="B", score=0.95),
            Chunk(document_id="doc3", chunk_id=0, content="C", score=0.85),
        ]
        result = reciprocal_rank_fusion([list1, list2])
        assert len(result) == 3
        # doc2 should be ranked higher due to appearing in both lists
        doc_ids = [c.document_id for c in result]
        assert "doc2" in doc_ids

    def test_with_weights(self):
        list1 = [
            Chunk(document_id="doc1", chunk_id=0, content="A", score=0.9),
        ]
        list2 = [
            Chunk(document_id="doc2", chunk_id=0, content="B", score=0.9),
        ]
        # Weight list2 higher
        result = reciprocal_rank_fusion([list1, list2], weights=[1.0, 2.0])
        assert len(result) == 2
        # doc2 should be ranked higher due to higher weight
        assert result[0].document_id == "doc2"


class TestLinearCombination:
    """Tests for linear combination ranking."""

    def test_empty_lists(self):
        result = linear_combination([])
        assert result == []

    def test_single_list(self):
        chunks = [
            Chunk(document_id="doc1", chunk_id=0, content="A", score=0.9),
            Chunk(document_id="doc2", chunk_id=0, content="B", score=0.8),
        ]
        result = linear_combination([chunks])
        assert len(result) == 2

    def test_merge_with_normalization(self):
        list1 = [
            Chunk(document_id="doc1", chunk_id=0, content="A", score=100),
            Chunk(document_id="doc2", chunk_id=0, content="B", score=50),
        ]
        list2 = [
            Chunk(document_id="doc2", chunk_id=0, content="B", score=1.0),
            Chunk(document_id="doc3", chunk_id=0, content="C", score=0.5),
        ]
        result = linear_combination([list1, list2], normalize=True)
        assert len(result) == 3
        # All scores should be in reasonable range after normalization
        for chunk in result:
            assert 0 <= chunk.score <= 1


class TestRerankByRelevance:
    """Tests for relevance-based reranking."""

    def test_empty_chunks(self):
        result = rerank_by_relevance([], "test query")
        assert result == []

    def test_keyword_matching(self):
        chunks = [
            Chunk(document_id="doc1", chunk_id=0, content="Python programming", score=0.5),
            Chunk(document_id="doc2", chunk_id=0, content="JavaScript basics", score=0.8),
            Chunk(document_id="doc3", chunk_id=0, content="Python and JavaScript", score=0.6),
        ]
        result = rerank_by_relevance(chunks, "Python")
        # Python-containing chunks should rank higher
        assert "Python" in result[0].content

    def test_title_weighting(self):
        chunks = [
            Chunk(
                document_id="doc1",
                chunk_id=0,
                content="Some content",
                title="Python Guide",
                score=0.5,
            ),
            Chunk(
                document_id="doc2",
                chunk_id=0,
                content="Python content here",
                title="Other Guide",
                score=0.5,
            ),
        ]
        result = rerank_by_relevance(chunks, "Python")
        # Title match should weigh higher
        assert result[0].title == "Python Guide"

    def test_top_k_limit(self):
        chunks = [
            Chunk(document_id=f"doc{i}", chunk_id=0, content=f"Content {i}", score=0.5)
            for i in range(10)
        ]
        result = rerank_by_relevance(chunks, "Content", top_k=3)
        assert len(result) == 3
