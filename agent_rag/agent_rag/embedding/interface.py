"""Embedding interface definitions."""

from abc import ABC, abstractmethod
from typing import Optional

from agent_rag.core.config import EmbeddingConfig


class Embedder(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.config.dimension

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self.config.model

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts.

        Args:
            texts: Texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    def embed_query(self, query: str) -> list[float]:
        """
        Embed a query (may use different model/prefix for some providers).

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        return self.embed(query)

    def embed_document(self, document: str) -> list[float]:
        """
        Embed a document (may use different model/prefix for some providers).

        Args:
            document: Document text

        Returns:
            Embedding vector
        """
        return self.embed(document)
