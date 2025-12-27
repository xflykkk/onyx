"""Tests for citation system."""

import pytest
from agent_rag.core.models import Chunk, Citation
from agent_rag.citation.processor import (
    DynamicCitationProcessor,
    CitationExtractor,
)
from agent_rag.citation.utils import (
    format_citation_reference,
    format_citation_list,
    format_citation_for_prompt,
    chunks_to_citations,
    remap_citations_in_text,
    validate_citation_coverage,
)


class TestDynamicCitationProcessor:
    """Tests for DynamicCitationProcessor."""

    @pytest.fixture
    def sample_chunks(self):
        return [
            Chunk(document_id="doc1", chunk_id=0, content="Content 1", title="Doc 1"),
            Chunk(document_id="doc2", chunk_id=0, content="Content 2", title="Doc 2"),
            Chunk(document_id="doc3", chunk_id=0, content="Content 3", title="Doc 3"),
        ]

    def test_process_simple_citation(self, sample_chunks):
        processor = DynamicCitationProcessor(sample_chunks)
        result = processor.process_complete_text("This is from [1].")
        assert "[1]" in result
        citations = processor.get_citations()
        assert len(citations) == 1
        assert citations[0].document_id == "doc1"

    def test_process_multiple_citations(self, sample_chunks):
        processor = DynamicCitationProcessor(sample_chunks)
        result = processor.process_complete_text("From [1] and [2].")
        citations = processor.get_citations()
        assert len(citations) == 2

    def test_citation_folding_same_document(self):
        chunks = [
            Chunk(document_id="doc1", chunk_id=0, content="Part 1"),
            Chunk(document_id="doc1", chunk_id=1, content="Part 2"),
            Chunk(document_id="doc2", chunk_id=0, content="Other"),
        ]
        processor = DynamicCitationProcessor(chunks, fold_citations=True)
        result = processor.process_complete_text("From [1] and [2].")
        citations = processor.get_citations()
        # Should fold to 1 citation since both are from doc1
        assert len(citations) == 1

    def test_streaming_tokens(self, sample_chunks):
        processor = DynamicCitationProcessor(sample_chunks)

        # Simulate streaming
        tokens = ["This ", "is ", "from ", "[", "1", "]", "."]
        result = ""
        for token in tokens:
            result += processor.process_token(token)
        result += processor.flush()

        assert "[1]" in result

    def test_reset(self, sample_chunks):
        processor = DynamicCitationProcessor(sample_chunks)
        processor.process_complete_text("From [1].")
        assert len(processor.get_citations()) == 1

        processor.reset()
        assert len(processor.get_citations()) == 0


class TestCitationExtractor:
    """Tests for CitationExtractor."""

    def test_extract_single_citation(self):
        ids = CitationExtractor.extract_citation_ids("This is cited [1].")
        assert ids == [1]

    def test_extract_multiple_citations(self):
        ids = CitationExtractor.extract_citation_ids("From [1] and [2] and [3].")
        assert ids == [1, 2, 3]

    def test_extract_combined_citations(self):
        ids = CitationExtractor.extract_citation_ids("From [1,2,3].")
        assert ids == [1, 2, 3]

    def test_validate_citations_valid(self):
        is_valid, invalid = CitationExtractor.validate_citations(
            "From [1] and [2].", max_citation_id=3
        )
        assert is_valid
        assert invalid == []

    def test_validate_citations_invalid(self):
        is_valid, invalid = CitationExtractor.validate_citations(
            "From [1] and [5].", max_citation_id=3
        )
        assert not is_valid
        assert 5 in invalid

    def test_remove_citations(self):
        result = CitationExtractor.remove_citations("This [1] is [2] text.")
        assert result == "This  is  text."

    def test_count_citations(self):
        counts = CitationExtractor.count_citations("From [1] and [1] and [2].")
        assert counts[1] == 2
        assert counts[2] == 1


class TestCitationUtils:
    """Tests for citation utility functions."""

    def test_format_citation_reference(self):
        assert format_citation_reference(1) == "[1]"
        assert format_citation_reference(10) == "[10]"

    def test_format_citation_list(self):
        citations = [
            Citation(citation_id=1, document_id="doc1", chunk_id=0, content="C1", title="T1"),
            Citation(citation_id=2, document_id="doc2", chunk_id=0, content="C2", title="T2"),
        ]
        result = format_citation_list(citations)
        assert "[1]" in result
        assert "[2]" in result
        assert "T1" in result
        assert "T2" in result

    def test_format_citation_for_prompt(self):
        chunks = [
            Chunk(document_id="doc1", chunk_id=0, content="Content 1", title="Title 1"),
            Chunk(document_id="doc2", chunk_id=0, content="Content 2", title="Title 2"),
        ]
        result = format_citation_for_prompt(chunks)
        assert "[1]" in result
        assert "[2]" in result
        assert "Content 1" in result

    def test_chunks_to_citations(self):
        chunks = [
            Chunk(document_id="doc1", chunk_id=0, content="C1"),
            Chunk(document_id="doc2", chunk_id=0, content="C2"),
        ]
        citations = chunks_to_citations(chunks)
        assert len(citations) == 2
        assert citations[0].citation_id == 1
        assert citations[1].citation_id == 2

    def test_remap_citations_in_text(self):
        text = "From [1] and [2] and [3]."
        mapping = {1: 10, 2: 20, 3: 30}
        result = remap_citations_in_text(text, mapping)
        assert "[10]" in result
        assert "[20]" in result
        assert "[30]" in result

    def test_validate_citation_coverage(self):
        citations = [
            Citation(citation_id=1, document_id="doc1", chunk_id=0, content="C1"),
            Citation(citation_id=2, document_id="doc2", chunk_id=0, content="C2"),
            Citation(citation_id=3, document_id="doc3", chunk_id=0, content="C3"),
        ]
        report = validate_citation_coverage("From [1] and [2].", citations)
        assert report["total_citations"] == 3
        assert report["used_count"] == 2
        assert report["unused_count"] == 1
        assert 3 in report["unused_ids"]
