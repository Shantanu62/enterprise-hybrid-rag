
from typing import Any

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore


class SearchService:
    """Retrieve relevant document chunks using tenant-scoped semantic search."""

    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()

    @staticmethod
    def _validate_tenant_id(tenant_id: str) -> str:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id must not be empty.")

        return tenant_id.strip()

    def search(
        self,
        query: str,
        tenant_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return relevant document chunks from one tenant only."""

        tenant_id = self._validate_tenant_id(tenant_id)

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must not be empty.")

        if limit <= 0:
            raise ValueError("Limit must be greater than 0.")

        query_vector = self.embedder.embed_query(query.strip())

        results = self.vector_store.search(
            query_vector=query_vector,
            tenant_id=tenant_id,
            limit=limit,
        )

        return results

    def close(self) -> None:
        """Release the Qdrant client connection."""
        self.vector_store.close()
