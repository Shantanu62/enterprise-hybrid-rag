
from typing import Any

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore


class SearchService:
    """Retrieve relevant document chunks using semantic search."""

    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the most relevant document chunks for a query."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must not be empty.")

        if limit <= 0:
            raise ValueError("Limit must be greater than 0.")

        query_vector = self.embedder.embed_query(query.strip())

        results = self.vector_store.search(
            query_vector=query_vector,
            limit=limit,
        )

        return results

    def close(self) -> None:
        """Release the Qdrant client connection."""
        self.vector_store.close()
