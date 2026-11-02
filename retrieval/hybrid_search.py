
import time
from typing import Any

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from retrieval.bm25_index import BM25IndexManager


class HybridSearchService:
    """Combine tenant-scoped BM25 and vector search using RRF."""

    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()

        self.bm25_index_manager = BM25IndexManager(
            self.vector_store
        )

        self.last_metrics: dict[str, float] = {}

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
        candidate_multiplier: int = 3,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:

        total_start = time.perf_counter()
        self.last_metrics = {}

        tenant_id = self._validate_tenant_id(tenant_id)

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must not be empty.")

        if limit <= 0 or candidate_multiplier <= 0 or rrf_k <= 0:
            raise ValueError(
                "Search limits and rrf_k must be greater than 0."
            )

        query = query.strip()

        # 1. Load only this tenant's cached documents.
        cache_start = time.perf_counter()

        documents = self.bm25_index_manager.get_documents(
            tenant_id=tenant_id
        )

        cache_time = time.perf_counter() - cache_start

        if not documents:
            bm25_metrics = self.bm25_index_manager.get_metrics(
                tenant_id
            )

            self.last_metrics = {
                "bm25_cache_load_ms": cache_time * 1000,
                "bm25_rebuild_ms": bm25_metrics.get(
                    "bm25_rebuild_ms", 0.0
                ),
                "bm25_document_count": 0.0,
                "total_hybrid_search_ms": (
                    time.perf_counter() - total_start
                ) * 1000,
            }

            return []

        # 2. Generate query embedding.
        embedding_start = time.perf_counter()

        query_vector = self.embedder.embed_query(query)

        embedding_time = time.perf_counter() - embedding_start

        # 3. Tenant-filtered Qdrant vector search.
        vector_start = time.perf_counter()

        vector_results = self.vector_store.search(
            query_vector=query_vector,
            tenant_id=tenant_id,
            limit=limit * candidate_multiplier,
        )

        vector_rankings = []

        for result in vector_results:
            point_id = result["id"]

            if point_id in documents:
                vector_rankings.append(point_id)
                documents[point_id]["vector_score"] = result["score"]

        vector_time = time.perf_counter() - vector_start

        # 4. Search only this tenant's BM25 index.
        bm25_start = time.perf_counter()

        bm25_results = self.bm25_index_manager.search(
            query=query,
            tenant_id=tenant_id,
            limit=len(documents),
        )

        bm25_rankings = []

        for point_id, score in bm25_results:
            if point_id in documents:
                bm25_rankings.append(point_id)
                documents[point_id]["bm25_score"] = score

        bm25_time = time.perf_counter() - bm25_start

        # 5. Reciprocal Rank Fusion.
        rrf_start = time.perf_counter()

        for rankings in (vector_rankings, bm25_rankings):
            for rank, point_id in enumerate(rankings, start=1):
                documents[point_id]["rrf_score"] += (
                    1.0 / (rrf_k + rank)
                )

        final_results = sorted(
            documents.values(),
            key=lambda item: (
                item["rrf_score"],
                item["vector_score"] or 0.0,
            ),
            reverse=True,
        )[:limit]

        rrf_time = time.perf_counter() - rrf_start

        # 6. Tenant-specific performance metrics.
        total_time = time.perf_counter() - total_start

        bm25_metrics = self.bm25_index_manager.get_metrics(
            tenant_id
        )

        self.last_metrics = {
            "bm25_cache_load_ms": cache_time * 1000,
            "bm25_rebuild_ms": bm25_metrics.get(
                "bm25_rebuild_ms", 0.0
            ),
            "bm25_document_count": bm25_metrics.get(
                "bm25_document_count", 0.0
            ),
            "query_embedding_ms": embedding_time * 1000,
            "vector_search_ms": vector_time * 1000,
            "bm25_search_ms": bm25_time * 1000,
            "rrf_ms": rrf_time * 1000,
            "total_hybrid_search_ms": total_time * 1000,
        }

        return final_results

    def close(self) -> None:
        """Close the Qdrant client connection."""
        self.vector_store.close()
