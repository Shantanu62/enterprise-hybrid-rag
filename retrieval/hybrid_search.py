
import re
import time
from typing import Any

from rank_bm25 import BM25Plus

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore


def tokenize(text: str) -> list[str]:
    """Convert text into lowercase word tokens."""
    return re.findall(r"\b\w+\b", text.lower())


class HybridSearchService:
    """Combine vector search and BM25Plus using Reciprocal Rank Fusion."""

    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()

        # Stores timing information for the latest search.
        self.last_metrics: dict[str, float] = {}

    def search(
        self,
        query: str,
        limit: int = 5,
        candidate_multiplier: int = 3,
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:

        total_start = time.perf_counter()

        self.last_metrics = {}

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must not be empty.")

        if limit <= 0 or candidate_multiplier <= 0 or rrf_k <= 0:
            raise ValueError("Search limits and rrf_k must be greater than 0.")

        query = query.strip()

        # ---------------------------------
        # 1. Load documents from Qdrant
        # ---------------------------------
        scroll_start = time.perf_counter()

        all_points = []
        offset = None

        while True:
            points, next_offset = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            all_points.extend(points)

            if next_offset is None:
                break

            offset = next_offset

        scroll_time = time.perf_counter() - scroll_start

        documents = {}

        for point in all_points:
            payload = point.payload or {}
            text = payload.get("text", "")

            if isinstance(text, str) and text.strip():
                documents[str(point.id)] = {
                    "text": text,
                    "metadata": payload.get("metadata", {}),
                    "vector_score": None,
                    "bm25_score": 0.0,
                    "rrf_score": 0.0,
                }

        if not documents:
            self.last_metrics = {
                "qdrant_scroll_ms": scroll_time * 1000,
                "total_hybrid_search_ms": (
                    time.perf_counter() - total_start
                ) * 1000,
            }

            return []

        # ---------------------------------
        # 2. Query Embedding
        # ---------------------------------
        embedding_start = time.perf_counter()

        query_vector = self.embedder.embed_query(query)

        embedding_time = time.perf_counter() - embedding_start

        # ---------------------------------
        # 3. Vector Search
        # ---------------------------------
        vector_start = time.perf_counter()

        vector_response = self.vector_store.client.query_points(
            collection_name=self.vector_store.collection_name,
            query=query_vector,
            limit=min(
                len(documents),
                limit * candidate_multiplier,
            ),
            with_payload=True,
        )

        vector_rankings = []

        for point in vector_response.points:
            point_id = str(point.id)

            if point_id in documents:
                vector_rankings.append(point_id)
                documents[point_id]["vector_score"] = point.score

        vector_time = time.perf_counter() - vector_start

        # ---------------------------------
        # 4. BM25Plus Keyword Search
        # ---------------------------------
        bm25_start = time.perf_counter()

        corpus_ids = list(documents.keys())

        tokenized_corpus = [
            tokenize(documents[point_id]["text"])
            for point_id in corpus_ids
        ]

        query_tokens = tokenize(query)
        bm25_rankings = []

        if query_tokens and any(tokenized_corpus):
            bm25 = BM25Plus(tokenized_corpus)
            scores = bm25.get_scores(query_tokens)

            query_terms = set(query_tokens)

            matching_indices = [
                index
                for index, tokens in enumerate(tokenized_corpus)
                if query_terms.intersection(tokens)
            ]

            matching_indices.sort(
                key=lambda index: scores[index],
                reverse=True,
            )

            bm25_rankings = [
                corpus_ids[index]
                for index in matching_indices
            ]

            for index in matching_indices:
                documents[corpus_ids[index]]["bm25_score"] = float(
                    scores[index]
                )

        bm25_time = time.perf_counter() - bm25_start

        # ---------------------------------
        # 5. Reciprocal Rank Fusion
        # ---------------------------------
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

        # ---------------------------------
        # 6. Save Performance Metrics
        # ---------------------------------
        total_time = time.perf_counter() - total_start

        self.last_metrics = {
            "qdrant_scroll_ms": scroll_time * 1000,
            "query_embedding_ms": embedding_time * 1000,
            "vector_search_ms": vector_time * 1000,
            "bm25_search_ms": bm25_time * 1000,
            "rrf_ms": rrf_time * 1000,
            "total_hybrid_search_ms": total_time * 1000,
        }

        return final_results

    def close(self) -> None:
        self.vector_store.close()
