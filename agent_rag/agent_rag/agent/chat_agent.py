"""Chat agent implementation for Agent RAG."""

from typing import Any, Iterator, Optional

from agent_rag.agent.base import AgentState, BaseAgent
from agent_rag.agent.step import AgentStep
from agent_rag.citation.processor import DynamicCitationProcessor
from agent_rag.citation.utils import chunks_to_citations, format_citation_list
from agent_rag.core.callbacks import AgentCallback, StreamCallback, ToolCallback
from agent_rag.core.config import AgentConfig
from agent_rag.core.models import AgentResponse, Chunk, Citation, Message, ToolCall
from agent_rag.llm.interface import LLM
from agent_rag.tools.registry import ToolRegistry
from agent_rag.tools.runner import ToolRunner
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant with access to search tools.

When answering questions:
1. Use the search tool to find relevant information
2. Cite your sources using [N] notation where N is the source number
3. Be accurate and helpful
4. If you don't know something, say so

Available tools will help you search through documents and the web."""


class ChatAgent(BaseAgent):
    """
    Chat agent for conversational RAG.

    Implements the agent loop:
    1. Receive user query
    2. Optionally call tools (search, etc.)
    3. Generate response with citations
    4. Repeat until done or max steps reached
    """

    def __init__(
        self,
        llm: LLM,
        config: Optional[AgentConfig] = None,
        tool_registry: Optional[ToolRegistry] = None,
        tool_runner: Optional[ToolRunner] = None,
        system_prompt: Optional[str] = None,
        stream_callback: Optional[StreamCallback] = None,
        tool_callback: Optional[ToolCallback] = None,
        agent_callback: Optional[AgentCallback] = None,
    ) -> None:
        """
        Initialize the chat agent.

        Args:
            llm: LLM provider
            config: Agent configuration
            tool_registry: Registry of available tools
            tool_runner: Optional tool runner
            system_prompt: Optional custom system prompt
            stream_callback: Callback for streaming tokens
            tool_callback: Callback for tool execution events
            agent_callback: Callback for agent lifecycle events
        """
        super().__init__(
            llm=llm,
            config=config,
            tool_registry=tool_registry,
            stream_callback=stream_callback,
            tool_callback=tool_callback,
            agent_callback=agent_callback,
        )

        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.tool_runner = tool_runner or ToolRunner(self.tool_registry)
        self.step_executor = AgentStep(
            llm=llm,
            tool_registry=self.tool_registry,
            tool_runner=self.tool_runner,
        )

        # Track retrieved chunks for citations
        self._retrieved_chunks: list[Chunk] = []
        self._citation_processor: Optional[DynamicCitationProcessor] = None

    def reset(self) -> None:
        """Reset agent state."""
        super().reset()
        self._retrieved_chunks = []
        self._citation_processor = None

    def _initialize_conversation(self, query: str) -> None:
        """Initialize conversation with system prompt and user query."""
        self.reset()
        self.add_system_message(self.system_prompt)
        self.add_user_message(query)

    def _process_tool_results(
        self,
        tool_results: list[tuple[ToolCall, str]],
    ) -> None:
        """Process tool results and extract chunks."""
        for tool_call, result in tool_results:
            self.add_tool_result(tool_call.id, result)

            # Track tool call
            self.state.tool_calls.append(tool_call)

            # Extract chunks from search results if available
            if hasattr(self.tool_runner, 'last_result'):
                last_result = self.tool_runner.last_result
                if last_result and last_result.rich_response:
                    chunks = last_result.rich_response.get("chunks", [])
                    if isinstance(chunks, list):
                        for chunk in chunks:
                            if isinstance(chunk, Chunk):
                                self._retrieved_chunks.append(chunk)

    def run(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Run the chat agent.

        Args:
            query: User query
            context: Optional context for tools

        Returns:
            AgentResponse with result
        """
        self._notify_start(query)
        self._initialize_conversation(query)

        try:
            while self.should_continue():
                self.state.step_count += 1

                # Execute step
                step_result = self.step_executor.execute(
                    messages=self.state.messages,
                    tools=self.get_tool_definitions(),
                )

                self.state.total_tokens += step_result.tokens_used

                # Add assistant message
                if step_result.content or step_result.tool_calls:
                    self.add_assistant_message(
                        content=step_result.content,
                        tool_calls=step_result.tool_calls if step_result.tool_calls else None,
                    )
                    self._notify_step(
                        self.state.step_count,
                        self.state.messages[-1],
                    )

                # Execute tool calls if any
                if step_result.tool_calls:
                    for tc in step_result.tool_calls:
                        self._notify_tool_start(tc)

                    tool_results = self.step_executor.execute_tools(
                        step_result.tool_calls,
                        context=context,
                    )

                    for tc, result in tool_results:
                        self._notify_tool_end(tc, result)

                    self._process_tool_results(tool_results)

                # Check if we should stop
                if not step_result.should_continue:
                    self.state.should_stop = True
                    break

            # Build response
            final_content = self._get_final_content()
            citations = self._build_citations()

            response = AgentResponse(
                content=final_content,
                citations=citations,
                tool_calls=self.state.tool_calls,
                messages=self.state.messages,
                metadata={
                    "steps": self.state.step_count,
                    "tokens": self.state.total_tokens,
                },
            )

            self._notify_end(response)
            return response

        except Exception as e:
            self._notify_error(e)
            raise

    def run_stream(
        self,
        query: str,
        context: Optional[dict[str, Any]] = None,
    ) -> Iterator[str]:
        """
        Run the chat agent with streaming.

        Args:
            query: User query
            context: Optional context for tools

        Yields:
            Response tokens
        """
        self._notify_start(query)
        self._initialize_conversation(query)

        try:
            while self.should_continue():
                self.state.step_count += 1

                accumulated_content = ""
                step_result = None

                # Stream step execution
                for token, result in self.step_executor.execute_stream(
                    messages=self.state.messages,
                    tools=self.get_tool_definitions(),
                ):
                    if token:
                        accumulated_content += token
                        self._stream_token(token)
                        yield token

                    if result:
                        step_result = result

                if step_result is None:
                    break

                self.state.total_tokens += step_result.tokens_used

                # Add assistant message
                if accumulated_content or step_result.tool_calls:
                    self.add_assistant_message(
                        content=accumulated_content,
                        tool_calls=step_result.tool_calls if step_result.tool_calls else None,
                    )

                # Execute tool calls if any
                if step_result.tool_calls:
                    for tc in step_result.tool_calls:
                        self._notify_tool_start(tc)

                    tool_results = self.step_executor.execute_tools(
                        step_result.tool_calls,
                        context=context,
                    )

                    for tc, result in tool_results:
                        self._notify_tool_end(tc, result)

                    self._process_tool_results(tool_results)

                    # Stream tool execution indicator
                    yield "\n[Searching...]\n"

                if not step_result.should_continue:
                    self.state.should_stop = True
                    break

            # Stream citations if any
            citations = self._build_citations()
            if citations:
                citation_text = "\n\n" + format_citation_list(citations)
                yield citation_text

        except Exception as e:
            self._notify_error(e)
            raise

    def _get_final_content(self) -> str:
        """Get final response content from messages."""
        # Find last assistant message without tool calls
        for msg in reversed(self.state.messages):
            if msg.role == "assistant" and not msg.tool_calls:
                return msg.content
            elif msg.role == "assistant" and msg.content:
                return msg.content

        return ""

    def _build_citations(self) -> list[Citation]:
        """Build citations from retrieved chunks."""
        if not self._retrieved_chunks:
            return []

        # Deduplicate by document_id
        seen_docs: set[str] = set()
        unique_chunks: list[Chunk] = []

        for chunk in self._retrieved_chunks:
            if chunk.document_id not in seen_docs:
                seen_docs.add(chunk.document_id)
                unique_chunks.append(chunk)

        return chunks_to_citations(unique_chunks)

    def continue_conversation(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Continue an existing conversation.

        Args:
            message: New user message
            context: Optional context for tools

        Returns:
            AgentResponse with result
        """
        self.add_user_message(message)
        self.state.should_stop = False
        self.state.step_count = 0

        # Clear retrieved chunks for new turn
        self._retrieved_chunks = []

        return self._run_loop(context)

    def _run_loop(
        self,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Run the agent loop (internal helper)."""
        while self.should_continue():
            self.state.step_count += 1

            step_result = self.step_executor.execute(
                messages=self.state.messages,
                tools=self.get_tool_definitions(),
            )

            self.state.total_tokens += step_result.tokens_used

            if step_result.content or step_result.tool_calls:
                self.add_assistant_message(
                    content=step_result.content,
                    tool_calls=step_result.tool_calls if step_result.tool_calls else None,
                )

            if step_result.tool_calls:
                tool_results = self.step_executor.execute_tools(
                    step_result.tool_calls,
                    context=context,
                )
                self._process_tool_results(tool_results)

            if not step_result.should_continue:
                self.state.should_stop = True
                break

        final_content = self._get_final_content()
        citations = self._build_citations()

        return AgentResponse(
            content=final_content,
            citations=citations,
            tool_calls=self.state.tool_calls,
            messages=self.state.messages,
            metadata={
                "steps": self.state.step_count,
                "tokens": self.state.total_tokens,
            },
        )
