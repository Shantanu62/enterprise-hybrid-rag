
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.vector_store import VectorStore


def create_vector_store():
    """Create VectorStore without initializing a real Qdrant connection."""
    store = VectorStore.__new__(VectorStore)
    store.collection_name = "enterprise_documents"
    store.client = MagicMock()
    return store


def test_get_previous_version_ids_returns_unique_sorted_ids():
    store = create_vector_store()

    points = [
        SimpleNamespace(
            payload={"metadata": {"version_id": "version-b"}}
        ),
        SimpleNamespace(
            payload={"metadata": {"version_id": "version-a"}}
        ),
        SimpleNamespace(
            payload={"metadata": {"version_id": "version-b"}}
        ),
        SimpleNamespace(
            payload={"metadata": {"version_id": "version-current"}}
        ),
        SimpleNamespace(
            payload={"metadata": {}}
        ),
        SimpleNamespace(
            payload=None
        ),
    ]

    store.client.scroll.return_value = (points, None)

    result = store.get_previous_version_ids(
        tenant_id="tenant-123",
        document_id="document-123",
        current_version_id="version-current",
    )

    assert result == ["version-a", "version-b"]
    store.client.scroll.assert_called_once()


def test_get_previous_version_ids_handles_multiple_pages():
    store = create_vector_store()

    first_page = [
        SimpleNamespace(
            payload={"metadata": {"version_id": "version-b"}}
        )
    ]

    second_page = [
        SimpleNamespace(
            payload={"metadata": {"version_id": "version-a"}}
        )
    ]

    store.client.scroll.side_effect = [
        (first_page, "next-page"),
        (second_page, None),
    ]

    result = store.get_previous_version_ids(
        tenant_id="tenant-123",
        document_id="document-123",
        current_version_id="version-current",
    )

    assert result == ["version-a", "version-b"]
    assert store.client.scroll.call_count == 2


@pytest.mark.parametrize(
    "tenant_id, document_id, current_version_id",
    [
        ("", "document-123", "version-123"),
        ("tenant-123", "", "version-123"),
        ("tenant-123", "document-123", ""),
    ],
)
def test_get_previous_version_ids_rejects_empty_identifiers(
    tenant_id,
    document_id,
    current_version_id,
):
    store = create_vector_store()

    with pytest.raises(ValueError):
        store.get_previous_version_ids(
            tenant_id=tenant_id,
            document_id=document_id,
            current_version_id=current_version_id,
        )

    store.client.scroll.assert_not_called()
