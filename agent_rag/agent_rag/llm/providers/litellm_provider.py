"""LiteLLM-based LLM provider."""

import json
from typing import Any, Generator, Optional

from agent_rag.core.config import LLMConfig, ToolChoice
from agent_rag.core.exceptions import LLMError, LLMRateLimitError, LLMContextLengthError
from agent_rag.llm.interface import LLM, LLMMessage, LLMResponse, LLMToolCall, StreamChunk
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


class LiteLLMProvider(LLM):
    """LLM provider using LiteLLM."""

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure LiteLLM is initialized."""
        if self._initialized:
            return

        try:
            import litellm

            # Configure LiteLLM
            litellm.drop_params = True
            litellm.set_verbose = False

            # Set API key if provided
            if self.config.api_key:
                # LiteLLM uses environment variables or direct passing
                pass

            self._initialized = True
        except ImportError:
            raise LLMError(
                "LiteLLM is not installed. Install with: pip install litellm",
                model=self.config.model,
                provider=self.config.provider,
            )

    def _build_params(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Build parameters for LiteLLM call."""
        params: dict[str, Any] = {
            "model": self.config.model,
            "messages": [msg.to_dict() for msg in messages],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "stream": stream,
            "timeout": self.config.timeout,
        }

        # Add API key if provided
        if self.config.api_key:
            params["api_key"] = self.config.api_key

        # Add API base if provided
        if self.config.api_base:
            params["api_base"] = self.config.api_base

        # Add tools if provided
        if tools:
            params["tools"] = tools
            if tool_choice == ToolChoice.REQUIRED:
                params["tool_choice"] = "required"
            elif tool_choice == ToolChoice.NONE:
                params["tool_choice"] = "none"
            else:
                params["tool_choice"] = "auto"

        # Add reasoning model parameters
        if self.config.is_reasoning_model:
            params["reasoning_effort"] = self.config.reasoning_effort

        # Add extra options
        params.update(self.config.extra_options)

        return params

    def _parse_tool_calls(
        self,
        tool_calls: list[Any],
    ) -> list[LLMToolCall]:
        """Parse tool calls from LiteLLM response."""
        result = []
        for tc in tool_calls:
            try:
                # Handle both dict and object formats
                if isinstance(tc, dict):
                    tc_id = tc.get("id", "")
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    args_str = func.get("arguments", "{}")
                else:
                    tc_id = getattr(tc, "id", "")
                    func = getattr(tc, "function", None)
                    if func:
                        name = getattr(func, "name", "")
                        args_str = getattr(func, "arguments", "{}")
                    else:
                        continue

                # Parse arguments
                if isinstance(args_str, str):
                    try:
                        arguments = json.loads(args_str)
                    except json.JSONDecodeError:
                        arguments = {"raw": args_str}
                else:
                    arguments = args_str

                result.append(LLMToolCall(
                    id=tc_id,
                    name=name,
                    arguments=arguments,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse tool call: {e}")
                continue

        return result

    def _handle_error(self, error: Exception) -> None:
        """Handle LiteLLM errors."""
        error_str = str(error).lower()

        if "rate limit" in error_str or "rate_limit" in error_str:
            raise LLMRateLimitError(
                message=str(error),
                model=self.config.model,
                provider=self.config.provider,
            )
        elif "context length" in error_str or "token" in error_str:
            raise LLMContextLengthError(
                message=str(error),
                model=self.config.model,
                provider=self.config.provider,
            )
        else:
            raise LLMError(
                message=str(error),
                model=self.config.model,
                provider=self.config.provider,
            )

    def chat(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Synchronous chat completion."""
        self._ensure_initialized()

        import litellm

        params = self._build_params(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )

        try:
            response = litellm.completion(**params)
        except Exception as e:
            self._handle_error(e)
            raise  # Should not reach here

        # Parse response
        choice = response.choices[0]
        message = choice.message

        content = message.content or ""
        reasoning = None
        tool_calls: list[LLMToolCall] = []

        # Extract reasoning if present (for reasoning models)
        if hasattr(message, "reasoning_content") and message.reasoning_content:
            reasoning = message.reasoning_content
        elif hasattr(message, "reasoning") and message.reasoning:
            reasoning = message.reasoning

        # Parse tool calls
        if message.tool_calls:
            tool_calls = self._parse_tool_calls(message.tool_calls)

        # Extract usage
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            reasoning=reasoning,
            finish_reason=choice.finish_reason,
            usage=usage,
        )

    def chat_stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: ToolChoice = ToolChoice.AUTO,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Generator[StreamChunk, None, LLMResponse]:
        """Streaming chat completion."""
        self._ensure_initialized()

        import litellm

        params = self._build_params(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        try:
            response = litellm.completion(**params)
        except Exception as e:
            self._handle_error(e)
            raise  # Should not reach here

        # Accumulate response
        full_content = ""
        full_reasoning = ""
        accumulated_tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason = None

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            chunk_finish_reason = chunk.choices[0].finish_reason

            if chunk_finish_reason:
                finish_reason = chunk_finish_reason

            # Content
            content = ""
            if delta.content:
                content = delta.content
                full_content += content

            # Reasoning (for reasoning models)
            reasoning = ""
            is_reasoning = False
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                reasoning = delta.reasoning_content
                full_reasoning += reasoning
                is_reasoning = True

            # Tool calls
            tool_call_chunks: list[dict[str, Any]] = []
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if hasattr(tc, "index") else 0

                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }

                    if hasattr(tc, "id") and tc.id:
                        accumulated_tool_calls[idx]["id"] = tc.id

                    if hasattr(tc, "function") and tc.function:
                        if tc.function.name:
                            accumulated_tool_calls[idx]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            accumulated_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

                    tool_call_chunks.append(accumulated_tool_calls[idx])

            yield StreamChunk(
                content=content,
                reasoning=reasoning,
                tool_calls=tool_call_chunks,
                finish_reason=chunk_finish_reason,
                is_reasoning=is_reasoning,
            )

        # Parse final tool calls
        final_tool_calls: list[LLMToolCall] = []
        for tc_data in accumulated_tool_calls.values():
            try:
                args_str = tc_data["function"]["arguments"]
                arguments = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                arguments = {"raw": args_str}

            final_tool_calls.append(LLMToolCall(
                id=tc_data["id"],
                name=tc_data["function"]["name"],
                arguments=arguments,
            ))

        return LLMResponse(
            content=full_content,
            tool_calls=final_tool_calls,
            reasoning=full_reasoning if full_reasoning else None,
            finish_reason=finish_reason,
        )

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken if available."""
        try:
            import tiktoken

            # Try to get encoding for the model
            try:
                encoding = tiktoken.encoding_for_model(self.config.model)
            except KeyError:
                # Fall back to cl100k_base (GPT-4 encoding)
                encoding = tiktoken.get_encoding("cl100k_base")

            return len(encoding.encode(text))
        except ImportError:
            # Fall back to character-based estimation
            return len(text) // 4
