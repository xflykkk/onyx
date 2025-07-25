import abc
from collections.abc import Iterator
from typing import Literal

from langchain.schema.language_model import LanguageModelInput
from langchain_core.messages import AIMessageChunk
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from onyx.configs.app_configs import DISABLE_GENERATIVE_AI
from onyx.configs.app_configs import LOG_DANSWER_MODEL_INTERACTIONS
from onyx.configs.app_configs import LOG_INDIVIDUAL_MODEL_TOKENS
from onyx.utils.logger import setup_logger


logger = setup_logger()

ToolChoiceOptions = Literal["required"] | Literal["auto"] | Literal["none"]


class LLMConfig(BaseModel):
    model_provider: str
    model_name: str
    temperature: float
    api_key: str | None = None
    api_base: str | None = None
    api_version: str | None = None
    deployment_name: str | None = None
    credentials_file: str | None = None
    max_input_tokens: int
    # This disables the "model_" protected namespace for pydantic
    model_config = {"protected_namespaces": ()}


def log_prompt(prompt: LanguageModelInput) -> None:
    if isinstance(prompt, list):
        for ind, msg in enumerate(prompt):
            if isinstance(msg, AIMessageChunk):
                if msg.content:
                    log_msg = msg.content
                elif msg.tool_call_chunks:
                    log_msg = "Tool Calls: " + str(
                        [
                            {
                                key: value
                                for key, value in tool_call.items()
                                if key != "index"
                            }
                            for tool_call in msg.tool_call_chunks
                        ]
                    )
                else:
                    log_msg = ""
                logger.debug(f"Message {ind}:\n{log_msg}")
            else:
                logger.debug(f"Message {ind}:\n{msg.content}")
    if isinstance(prompt, str):
        logger.debug(f"Prompt:\n{prompt}")


class LLM(abc.ABC):
    """Mimics the LangChain LLM / BaseChatModel interfaces to make it easy
    to use these implementations to connect to a variety of LLM providers."""

    @property
    def requires_warm_up(self) -> bool:
        """Is this model running in memory and needs an initial call to warm it up?"""
        return False

    @property
    def requires_api_key(self) -> bool:
        return True

    @property
    @abc.abstractmethod
    def config(self) -> LLMConfig:
        raise NotImplementedError

    @abc.abstractmethod
    def log_model_configs(self) -> None:
        raise NotImplementedError

    def _precall(self, prompt: LanguageModelInput) -> None:
        if DISABLE_GENERATIVE_AI:
            raise Exception("Generative AI is disabled")
        if LOG_DANSWER_MODEL_INTERACTIONS:
            log_prompt(prompt)

    def invoke(
        self,
        prompt: LanguageModelInput,
        tools: list[dict] | None = None,
        tool_choice: ToolChoiceOptions | None = None,
        structured_response_format: dict | None = None,
        timeout_override: int | None = None,
        max_tokens: int | None = None,
    ) -> BaseMessage:
        from onyx.utils.think_tag_stripper import ThinkTagStripper
        
        self._precall(prompt)
        # TODO add a postcall to log model outputs independent of concrete class
        # implementation
        result = self._invoke_implementation(
            prompt,
            tools,
            tool_choice,
            structured_response_format,
            timeout_override,
            max_tokens,
        )
        
        # Filter out think tags from LLM responses to prevent them from propagating
        if isinstance(result.content, str):
            result.content = ThinkTagStripper.clean_think_tags(result.content)
        
        return result

    @abc.abstractmethod
    def _invoke_implementation(
        self,
        prompt: LanguageModelInput,
        tools: list[dict] | None = None,
        tool_choice: ToolChoiceOptions | None = None,
        structured_response_format: dict | None = None,
        timeout_override: int | None = None,
        max_tokens: int | None = None,
    ) -> BaseMessage:
        raise NotImplementedError

    def stream(
        self,
        prompt: LanguageModelInput,
        tools: list[dict] | None = None,
        tool_choice: ToolChoiceOptions | None = None,
        structured_response_format: dict | None = None,
        timeout_override: int | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[BaseMessage]:
        from onyx.utils.think_tag_stripper import ThinkTagStripper
        
        self._precall(prompt)
        # TODO add a postcall to log model outputs independent of concrete class
        # implementation
        messages = self._stream_implementation(
            prompt,
            tools,
            tool_choice,
            structured_response_format,
            timeout_override,
            max_tokens,
        )

        # Create a stateful stripper for streaming think tag removal
        stripper = ThinkTagStripper()
        
        tokens = []
        for message in messages:
            # Filter out think tags from streaming responses
            if isinstance(message.content, str):
                message.content = stripper.process_chunk(message.content)
            
            if LOG_INDIVIDUAL_MODEL_TOKENS:
                tokens.append(message.content)
            yield message

        if LOG_INDIVIDUAL_MODEL_TOKENS and tokens:
            logger.debug(f"Model Tokens: {tokens}")

    @abc.abstractmethod
    def _stream_implementation(
        self,
        prompt: LanguageModelInput,
        tools: list[dict] | None = None,
        tool_choice: ToolChoiceOptions | None = None,
        structured_response_format: dict | None = None,
        timeout_override: int | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[BaseMessage]:
        raise NotImplementedError
