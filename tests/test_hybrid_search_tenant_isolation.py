
from unittest.mock import MagicMock

import pytest

from retrieval.hybrid_search import HybridSearchService


@pytest.fixture
def service():
    instance = HybridSearchService.__new__(HybridSearchService)

    instance.embedder = MagicMock()
    instance.vector_store = MagicMock()
    instance.bm25_index_manager = MagicMock()
    instance.last_metrics = {}

    return instance


def make_document(point_id, text):
    return {
        "text": text,
        "metadata": {"tenant_id": "tenant-a"},
        "vector_score": None,
        "bm25_score": 0.0,
        "rrf_score": 0.0,
    }


def test_hybrid_search_passes_tenant_to_all_search_layers(service):
    service.bm25_index_manager.get_documents.return_value = {
        "point-a": make_document("point-a", "customer support")
    }

    service.embedder.embed_query.return_value = [0.1] * 384

    service.vector_store.search.return_value = [
        {"id": "point-a", "score": 0.95}
    ]

    service.bm25_index_manager.search.return_value = [
        ("point-a", 2.5)
    ]

    service.bm25_index_manager.get_metrics.return_value = {
        "bm25_rebuild_ms": 10.0,
        "bm25_document_count": 1.0,
    }

    results = service.search(
        query="customer support",
        tenant_id="tenant-a",
        limit=5,
    )

    assert len(results) == 1

    service.bm25_index_manager.get_documents.assert_called_once_with(
        tenant_id="tenant-a"
    )

    service.vector_store.search.assert_called_once_with(
        query_vector=[0.1] * 384,
        tenant_id="tenant-a",
        limit=15,
    )

    service.bm25_index_manager.search.assert_called_once_with(
        query="customer support",
        tenant_id="tenant-a",
        limit=1,
    )


def test_vector_results_outside_tenant_documents_are_excluded(service):
    service.bm25_index_manager.get_documents.return_value = {
        "tenant-a-point": make_document(
            "tenant-a-point",
            "customer support",
        )
    }

    service.embedder.embed_query.return_value = [0.1] * 384

    service.vector_store.search.return_value = [
        {"id": "tenant-a-point", "score": 0.95},
        {"id": "tenant-b-point", "score": 0.99},
    ]

    service.bm25_index_manager.search.return_value = []

    service.bm25_index_manager.get_metrics.return_value = {
        "bm25_rebuild_ms": 5.0,
        "bm25_document_count": 1.0,
    }

    results = service.search(
        query="customer support",
        tenant_id="tenant-a",
    )

    assert len(results) == 1
    assert results[0]["metadata"]["tenant_id"] == "tenant-a"

    assert all(
        result["metadata"]["tenant_id"] == "tenant-a"
        for result in results
    )


def test_empty_tenant_documents_skip_vector_and_embedding(service):
    service.bm25_index_manager.get_documents.return_value = {}
    service.bm25_index_manager.get_metrics.return_value = {
        "bm25_rebuild_ms": 0.0,
        "bm25_document_count": 0.0,
    }

    results = service.search(
        query="customer support",
        tenant_id="tenant-a",
    )

    assert results == []

    service.embedder.embed_query.assert_not_called()
    service.vector_store.search.assert_not_called()
    service.bm25_index_manager.search.assert_not_called()


@pytest.mark.parametrize(
    "tenant_id",
    ["", "   "],
)
def test_empty_tenant_id_is_rejected(service, tenant_id):
    with pytest.raises(ValueError):
        service.search(
            query="customer support",
            tenant_id=tenant_id,
        )

    service.bm25_index_manager.get_documents.assert_not_called()


@pytest.mark.parametrize(
    "query",
    ["", "   "],
)
def test_empty_query_is_rejected(service, query):
    with pytest.raises(ValueError):
        service.search(
            query=query,
            tenant_id="tenant-a",
        )


@pytest.mark.parametrize(
    "limit, candidate_multiplier, rrf_k",
    [
        (0, 3, 60),
        (5, 0, 60),
        (5, 3, 0),
    ],
)
def test_invalid_search_parameters_are_rejected(
    service,
    limit,
    candidate_multiplier,
    rrf_k,
):
    with pytest.raises(ValueError):
        service.search(
            query="customer support",
            tenant_id="tenant-a",
            limit=limit,
            candidate_multiplier=candidate_multiplier,
            rrf_k=rrf_k,
        )
