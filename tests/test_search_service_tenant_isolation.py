
from unittest.mock import MagicMock

import pytest

from retrieval.search_service import SearchService


@pytest.fixture
def service():
    instance = SearchService.__new__(SearchService)
    instance.embedder = MagicMock()
    instance.vector_store = MagicMock()
    instance.embedder.embed_query.return_value = [0.1] * 384

    return instance


def test_search_passes_tenant_to_vector_store(service):
    expected_results = [
        {
            "id": "point-a",
            "text": "Customer support document",
            "metadata": {"tenant_id": "tenant-a"},
            "score": 0.95,
        }
    ]

    service.vector_store.search.return_value = expected_results

    results = service.search(
        query="  customer support  ",
        tenant_id="tenant-a",
        limit=5,
    )

    assert results == expected_results

    service.embedder.embed_query.assert_called_once_with(
        "customer support"
    )

    service.vector_store.search.assert_called_once_with(
        query_vector=[0.1] * 384,
        tenant_id="tenant-a",
        limit=5,
    )


def test_search_rejects_empty_tenant_id(service):
    with pytest.raises(ValueError):
        service.search(
            query="customer support",
            tenant_id="",
        )

    service.embedder.embed_query.assert_not_called()
    service.vector_store.search.assert_not_called()


def test_search_rejects_empty_query(service):
    with pytest.raises(ValueError):
        service.search(
            query="   ",
            tenant_id="tenant-a",
        )

    service.embedder.embed_query.assert_not_called()
    service.vector_store.search.assert_not_called()


def test_search_rejects_invalid_limit(service):
    with pytest.raises(ValueError):
        service.search(
            query="customer support",
            tenant_id="tenant-a",
            limit=0,
        )

    service.embedder.embed_query.assert_not_called()
    service.vector_store.search.assert_not_called()


def test_close_closes_vector_store_client(service):
    service.close()

    service.vector_store.close.assert_called_once()
