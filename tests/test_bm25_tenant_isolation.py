
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from retrieval.bm25_index import BM25IndexManager


@pytest.fixture
def manager():
    vector_store = MagicMock()
    vector_store.collection_name = "enterprise_documents"

    return BM25IndexManager(vector_store)


def make_point(point_id, tenant_id, text):
    return SimpleNamespace(
        id=point_id,
        payload={
            "text": text,
            "metadata": {
                "tenant_id": tenant_id,
                "source": "test.txt",
            },
        },
    )


def test_rebuild_indexes_only_requested_tenant(manager):
    tenant_a_point = make_point(
        "point-a",
        "tenant-a",
        "enterprise customer support",
    )

    tenant_b_point = make_point(
        "point-b",
        "tenant-b",
        "enterprise financial services",
    )

    manager.vector_store.client.scroll.return_value = (
        [tenant_a_point, tenant_b_point],
        None,
    )

    manager.rebuild("tenant-a")

    documents = manager.get_documents("tenant-a")

    assert list(documents.keys()) == ["point-a"]
    assert documents["point-a"]["metadata"]["tenant_id"] == "tenant-a"

    manager.vector_store.client.scroll.assert_called_once()


def test_rebuild_uses_tenant_filter(manager):
    manager.vector_store.client.scroll.return_value = ([], None)

    manager.rebuild("tenant-a")

    scroll_kwargs = (
        manager.vector_store.client.scroll.call_args.kwargs
    )

    scroll_filter = scroll_kwargs["scroll_filter"]

    assert scroll_filter.must[0].key == "metadata.tenant_id"
    assert scroll_filter.must[0].match.value == "tenant-a"


def test_tenant_indexes_are_independent(manager):
    tenant_a_point = make_point(
        "point-a",
        "tenant-a",
        "customer support ticket",
    )

    tenant_b_point = make_point(
        "point-b",
        "tenant-b",
        "financial account",
    )

    manager.vector_store.client.scroll.side_effect = [
        ([tenant_a_point], None),
        ([tenant_b_point], None),
    ]

    manager.rebuild("tenant-a")
    manager.rebuild("tenant-b")

    tenant_a_documents = manager.get_documents("tenant-a")
    tenant_b_documents = manager.get_documents("tenant-b")

    assert list(tenant_a_documents.keys()) == ["point-a"]
    assert list(tenant_b_documents.keys()) == ["point-b"]

    assert "point-b" not in tenant_a_documents
    assert "point-a" not in tenant_b_documents


def test_invalidate_only_marks_requested_tenant_dirty(manager):
    manager.vector_store.client.scroll.return_value = ([], None)

    manager.rebuild("tenant-a")
    manager.rebuild("tenant-b")

    manager.invalidate("tenant-a")

    assert manager._tenant_indexes["tenant-a"].dirty is True
    assert manager._tenant_indexes["tenant-b"].dirty is False


def test_rebuild_handles_multiple_pages(manager):
    first_page = [
        make_point("point-a", "tenant-a", "customer support")
    ]

    second_page = [
        make_point("point-b", "tenant-a", "customer service")
    ]

    manager.vector_store.client.scroll.side_effect = [
        (first_page, "next-page"),
        (second_page, None),
    ]

    manager.rebuild("tenant-a")

    documents = manager.get_documents("tenant-a")

    assert set(documents.keys()) == {"point-a", "point-b"}
    assert manager.vector_store.client.scroll.call_count == 2


def test_search_returns_only_requested_tenant_results(manager):
    tenant_a_point = make_point(
        "point-a",
        "tenant-a",
        "enterprise customer support",
    )

    tenant_b_point = make_point(
        "point-b",
        "tenant-b",
        "enterprise customer support",
    )

    manager.vector_store.client.scroll.side_effect = [
        ([tenant_a_point], None),
        ([tenant_b_point], None),
    ]

    manager.rebuild("tenant-a")
    manager.rebuild("tenant-b")

    tenant_a_results = manager.search(
        query="enterprise support",
        tenant_id="tenant-a",
    )

    tenant_b_results = manager.search(
        query="enterprise support",
        tenant_id="tenant-b",
    )

    assert tenant_a_results
    assert tenant_b_results

    assert all(
        point_id == "point-a"
        for point_id, score in tenant_a_results
    )

    assert all(
        point_id == "point-b"
        for point_id, score in tenant_b_results
    )


@pytest.mark.parametrize("tenant_id", ["", "   "])
def test_empty_tenant_id_is_rejected(manager, tenant_id):
    with pytest.raises(ValueError):
        manager.rebuild(tenant_id)

    manager.vector_store.client.scroll.assert_not_called()
