
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from rank_bm25 import BM25Plus
from qdrant_client import models

from core.vector_store import VectorStore


def tokenize(text: str) -> list[str]:
    """Convert text into lowercase word tokens."""
    return re.findall(r"\b\w+\b", text.lower())


@dataclass
class TenantIndexState:
    """Store an isolated BM25 index for one tenant."""

    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    corpus_ids: list[str] = field(default_factory=list)
    document_terms: dict[str, set[str]] = field(default_factory=dict)
    bm25: BM25Plus | None = None
    dirty: bool = True
    last_metrics: dict[str, float] = field(default_factory=dict)


class BM25IndexManager:
    """Manage separate in-memory BM25 indexes for each tenant."""

    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store
        self._lock = threading.RLock()

        # Each tenant receives an independent index and cache.
        self._tenant_indexes: dict[str, TenantIndexState] = {}

    @staticmethod
    def _validate_tenant_id(tenant_id: str) -> str:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("tenant_id must not be empty.")

        return tenant_id.strip()

    def _get_state(self, tenant_id: str) -> TenantIndexState:
        """Get or create the index state for a tenant."""

        tenant_id = self._validate_tenant_id(tenant_id)

        with self._lock:
            if tenant_id not in self._tenant_indexes:
                self._tenant_indexes[tenant_id] = TenantIndexState()

            return self._tenant_indexes[tenant_id]

    def invalidate(self, tenant_id: str) -> None:
        """Invalidate only the specified tenant's cached index."""

        tenant_id = self._validate_tenant_id(tenant_id)

        with self._lock:
            state = self._get_state(tenant_id)
            state.dirty = True

    def rebuild(self, tenant_id: str) -> None:
        """Rebuild the BM25 index using only one tenant's documents."""

        tenant_id = self._validate_tenant_id(tenant_id)
        state = self._get_state(tenant_id)

        start_time = time.perf_counter()

        documents: dict[str, dict[str, Any]] = {}
        offset = None

        tenant_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                )
            ]
        )

        while True:
            points, next_offset = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection_name,
                scroll_filter=tenant_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                metadata = payload.get("metadata", {})
                text = payload.get("text", "")

                # Defensive ownership verification.
                if not isinstance(metadata, dict):
                    continue

                if metadata.get("tenant_id") != tenant_id:
                    continue

                if isinstance(text, str) and text.strip():
                    documents[str(point.id)] = {
                        "text": text,
                        "metadata": metadata.copy(),
                        "vector_score": None,
                        "bm25_score": 0.0,
                        "rrf_score": 0.0,
                    }

            if next_offset is None:
                break

            offset = next_offset

        corpus_ids = list(documents.keys())

        tokenized_corpus = [
            tokenize(documents[point_id]["text"])
            for point_id in corpus_ids
        ]

        document_terms = {
            point_id: set(tokens)
            for point_id, tokens in zip(corpus_ids, tokenized_corpus)
        }

        bm25 = (
            BM25Plus(tokenized_corpus)
            if tokenized_corpus and any(tokenized_corpus)
            else None
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        with self._lock:
            state.documents = documents
            state.corpus_ids = corpus_ids
            state.document_terms = document_terms
            state.bm25 = bm25
            state.dirty = False

            state.last_metrics = {
                "bm25_rebuild_ms": elapsed_ms,
                "bm25_document_count": float(len(documents)),
            }

    def ensure_ready(self, tenant_id: str) -> None:
        """Rebuild only when the specified tenant's index is outdated."""

        tenant_id = self._validate_tenant_id(tenant_id)
        state = self._get_state(tenant_id)

        with self._lock:
            if state.dirty:
                self.rebuild(tenant_id)

    def get_documents(
        self,
        tenant_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Return a snapshot of one tenant's indexed documents."""

        tenant_id = self._validate_tenant_id(tenant_id)
        self.ensure_ready(tenant_id)

        with self._lock:
            state = self._get_state(tenant_id)

            return {
                point_id: {
                    **document,
                    "metadata": document["metadata"].copy(),
                }
                for point_id, document in state.documents.items()
            }

    def search(
        self,
        query: str,
        tenant_id: str,
        limit: int = 5,
    ) -> list[tuple[str, float]]:
        """Return keyword matches from one tenant's BM25 index."""

        tenant_id = self._validate_tenant_id(tenant_id)

        if not isinstance(query, str):
            raise ValueError("query must be a string.")

        if limit <= 0:
            raise ValueError("limit must be greater than 0.")

        self.ensure_ready(tenant_id)

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        with self._lock:
            state = self._get_state(tenant_id)

            if state.bm25 is None:
                return []

            scores = state.bm25.get_scores(query_tokens)
            query_terms = set(query_tokens)

            matching_indices = [
                index
                for index, point_id in enumerate(state.corpus_ids)
                if query_terms.intersection(
                    state.document_terms[point_id]
                )
            ]

            matching_indices.sort(
                key=lambda index: scores[index],
                reverse=True,
            )

            return [
                (
                    state.corpus_ids[index],
                    float(scores[index]),
                )
                for index in matching_indices[:limit]
            ]

    def get_metrics(self, tenant_id: str) -> dict[str, float]:
        """Return metrics for one tenant's BM25 index."""

        tenant_id = self._validate_tenant_id(tenant_id)
        self.ensure_ready(tenant_id)

        with self._lock:
            state = self._get_state(tenant_id)
            return state.last_metrics.copy()
