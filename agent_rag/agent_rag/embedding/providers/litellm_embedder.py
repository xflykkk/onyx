"""LiteLLM-based embedding provider."""

from typing import Any

from agent_rag.core.config import EmbeddingConfig
from agent_rag.core.exceptions import EmbeddingError
from agent_rag.embedding.interface import Embedder
from agent_rag.utils.logger import get_logger

logger = get_logger(__name__)


class LiteLLMEmbedder(Embedder):
    """Embedding provider using LiteLLM."""

    def __init__(self, config: EmbeddingConfig) -> None:
        super().__init__(config)
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure LiteLLM is initialized."""
        if self._initialized:
            return

        try:
            import litellm
            self._initialized = True
        except ImportError:
            raise EmbeddingError(
                "LiteLLM is not installed. Install with: pip install litellm",
                model=self.config.model,
            )

    def _build_params(self, input_texts: list[str]) -> dict[str, Any]:
        """Build parameters for LiteLLM embedding call."""
        params: dict[str, Any] = {
            "model": self.config.model,
            "input": input_texts,
        }

        if self.config.api_key:
            params["api_key"] = self.config.api_key

        if self.config.api_base:
            params["api_base"] = self.config.api_base

        params.update(self.config.extra_options)

        return params

    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        self._ensure_initialized()

        import litellm

        params = self._build_params([text])

        try:
            response = litellm.embedding(**params)
            return response.data[0]["embedding"]
        except Exception as e:
            raise EmbeddingError(
                f"Failed to embed text: {e}",
                model=self.config.model,
            )

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        if not texts:
            return []

        self._ensure_initialized()

        import litellm

        # Process in batches
        all_embeddings: list[list[float]] = []
        batch_size = self.config.batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            params = self._build_params(batch)

            try:
                response = litellm.embedding(**params)
                # Sort by index to ensure correct order
                sorted_data = sorted(response.data, key=lambda x: x["index"])
                batch_embeddings = [item["embedding"] for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                raise EmbeddingError(
                    f"Failed to embed batch: {e}",
                    model=self.config.model,
                )

        return all_embeddings
