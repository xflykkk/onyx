"""Search tool implementing the 5-step search process."""

from dataclasses import dataclass
from typing import Any, Optional

from agent_rag.core.config import SearchConfig
from agent_rag.core.models import Chunk, SearchFilters, Section
from agent_rag.document_index.interface import DocumentIndex
from agent_rag.embedding.interface import Embedder
from agent_rag.llm.interface import LLM
from agent_rag.retrieval.pipeline import RetrievalPipeline
from agent_rag.tools.interface import Tool, ToolResponse
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchToolConfig:
    """Configuration for search tool."""
    document_index: DocumentIndex
    embedder: Embedder
    llm: Optional[LLM] = None  # For query expansion and selection
    search_config: Optional[SearchConfig] = None


class SearchTool(Tool[SearchToolConfig]):
    """
    Internal document search tool implementing the 5-step search process:

    1. Query Generation - Generate multiple query variants
    2. Recombination - Merge results using weighted RRF
    3. Selection - LLM selects most relevant documents
    4. Expansion - Expand chunks to include surrounding context
    5. Prompt Building - Build response for LLM
    """

    NAME = "internal_search"
    DESCRIPTION = """Search the internal knowledge base for relevant documents.
Use this tool to find information from indexed documents like company wikis,
documentation, Confluence pages, Google Docs, etc."""

    def __init__(
        self,
        document_index: DocumentIndex,
        embedder: Embedder,
        llm: Optional[LLM] = None,
        search_config: Optional[SearchConfig] = None,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id)
        self.document_index = document_index
        self.embedder = embedder
        self.llm = llm
        self.search_config = search_config or SearchConfig()
        self.pipeline = RetrievalPipeline(
            document_index=document_index,
            embedder=embedder,
            config=self.search_config,
        )

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    def tool_definition(self) -> dict[str, Any]:
        """Get tool definition."""
        return self.build_tool_definition(
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant documents",
                },
                "source_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of source types to filter (e.g., ['confluence', 'google_drive'])",
                },
            },
            required=["query"],
        )

    def run(
        self,
        override_kwargs: Optional[SearchToolConfig] = None,
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Execute the 5-step search process."""
        query = llm_kwargs.get("query", "")
        source_types = llm_kwargs.get("source_types")

        if not query:
            return ToolResponse(llm_response="Error: No query provided")

        # Use override config if provided
        config = override_kwargs
        document_index = config.document_index if config else self.document_index
        embedder = config.embedder if config else self.embedder
        llm = config.llm if config else self.llm
        search_config = config.search_config if config else self.search_config

        # Build filters
        filters = None
        if source_types:
            filters = SearchFilters(source_types=source_types)

        # Step 1: Query Generation (expand queries if LLM available)
        expanded_queries: list[str] = []
        if llm and search_config.enable_query_expansion:
            expanded_queries = self._generate_queries(query, llm)

        # Step 2: Recombination - handled by pipeline with RRF
        pipeline = RetrievalPipeline(
            document_index=document_index,
            embedder=embedder,
            config=search_config,
        )

        result = pipeline.retrieve(
            query=query,
            filters=filters,
            expanded_queries=expanded_queries,
        )

        if not result.chunks:
            return ToolResponse(
                llm_response="No relevant documents found for your query.",
                rich_response={"chunks": [], "sections": []},
            )

        # Step 3: Selection - LLM selects most relevant (if enabled)
        selected_chunks = result.chunks
        if llm and search_config.enable_document_selection:
            selected_chunks = self._select_documents(
                query=query,
                chunks=result.chunks,
                llm=llm,
                max_docs=search_config.max_documents_to_select,
            )

        # Step 4: Expansion - expand to sections
        sections = result.sections
        if not sections and search_config.enable_context_expansion:
            sections = pipeline.merge_adjacent_chunks(
                selected_chunks,
                max_gap=1,
            )

        # Step 5: Prompt Building - build response
        response_text, citation_mapping = self._build_response(
            query=query,
            chunks=selected_chunks,
            sections=sections,
        )

        return ToolResponse(
            llm_response=response_text,
            rich_response={
                "chunks": [c.to_dict() for c in selected_chunks],
                "sections": [s.to_dict() for s in sections],
            },
            citation_mapping=citation_mapping,
        )

    def _generate_queries(
        self,
        query: str,
        llm: LLM,
    ) -> list[str]:
        """Step 1: Generate expanded queries."""
        from agent_rag.llm.interface import LLMMessage

        prompt = f"""Given the search query, generate 2-3 alternative phrasings that might help find relevant documents.
Return only the alternative queries, one per line, without numbering or explanations.

Original query: {query}

Alternative queries:"""

        messages = [
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = llm.chat(messages, max_tokens=200)
            lines = response.content.strip().split("\n")
            return [line.strip() for line in lines if line.strip()][:3]
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return []

    def _select_documents(
        self,
        query: str,
        chunks: list[Chunk],
        llm: LLM,
        max_docs: int = 10,
    ) -> list[Chunk]:
        """Step 3: LLM-based document selection."""
        if len(chunks) <= max_docs:
            return chunks

        from agent_rag.llm.interface import LLMMessage

        # Build document list for LLM
        doc_list = []
        for i, chunk in enumerate(chunks[:20]):  # Limit to top 20 for LLM
            preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
            doc_list.append(f"[{i}] {chunk.title or 'Untitled'}: {preview}")

        prompt = f"""Given the query and document previews, select the {max_docs} most relevant documents.
Return only the document numbers (e.g., 0, 3, 5), comma-separated.

Query: {query}

Documents:
{chr(10).join(doc_list)}

Most relevant document numbers:"""

        messages = [
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = llm.chat(messages, max_tokens=100)
            # Parse response
            selected_indices = []
            for part in response.content.replace(",", " ").split():
                try:
                    idx = int(part.strip())
                    if 0 <= idx < len(chunks):
                        selected_indices.append(idx)
                except ValueError:
                    continue

            if selected_indices:
                return [chunks[i] for i in selected_indices[:max_docs]]
        except Exception as e:
            logger.warning(f"Document selection failed: {e}")

        return chunks[:max_docs]

    def _build_response(
        self,
        query: str,
        chunks: list[Chunk],
        sections: list[Section],
    ) -> tuple[str, dict[int, str]]:
        """Step 5: Build response text with citations."""
        citation_mapping: dict[int, str] = {}
        response_parts = []

        response_parts.append(f"Found {len(chunks)} relevant documents for: {query}\n")

        for i, chunk in enumerate(chunks):
            citation_num = i + 1
            citation_mapping[citation_num] = chunk.document_id

            title = chunk.title or "Untitled Document"
            source = chunk.source_type or "unknown"

            response_parts.append(f"\n[{citation_num}] **{title}** (source: {source})")

            # Use section content if available
            section_content = None
            for section in sections:
                if section.center_chunk.unique_id == chunk.unique_id:
                    section_content = section.combined_content
                    break

            content = section_content or chunk.content
            # Truncate if too long
            if len(content) > 1000:
                content = content[:1000] + "..."

            response_parts.append(f"\n{content}\n")

        return "\n".join(response_parts), citation_mapping
