
from unittest.mock import MagicMock, call

import pytest

import ingestion.pipeline as pipeline_module
from ingestion.pipeline import IngestionPipeline


@pytest.fixture
def setup_pipeline(monkeypatch, tmp_path):
    """Create a pipeline with mocked external services."""

    file_path = tmp_path / "sample.txt"
    file_path.write_text("Sample document content.", encoding="utf-8")

    pipeline = IngestionPipeline.__new__(IngestionPipeline)

    pipeline.embedder = MagicMock()
    pipeline.vector_store = MagicMock()
    pipeline.bm25_index_manager = MagicMock()

    monkeypatch.setattr(
        pipeline_module,
        "load_document",
        lambda path: [{"text": "Sample document content."}],
    )

    monkeypatch.setattr(
        pipeline_module,
        "chunk_documents",
        lambda documents, chunk_size, chunk_overlap: [
            {
                "text": "Sample document chunk",
                "metadata": {"chunk_index": 0},
            }
        ],
    )

    pipeline.embedder.embed_texts.return_value = [[0.1] * 384]

    pipeline.vector_store.get_previous_version_ids.return_value = [
        "old-version-1",
        "old-version-2",
    ]

    pipeline.vector_store.add_documents.return_value = 1

    return pipeline, file_path


def test_ingestion_stores_new_version_before_deleting_old_versions(
    setup_pipeline,
):
    pipeline, file_path = setup_pipeline

    events = []

    def add_documents(**kwargs):
        events.append("store_new")
        return 1

    def delete_version(**kwargs):
        events.append("delete_old")

    pipeline.vector_store.add_documents.side_effect = add_documents
    pipeline.vector_store.delete_version.side_effect = delete_version

    result = pipeline.ingest_file(
        file_path=str(file_path),
        tenant_id="tenant-123",
        document_id="document-123",
        version_id="new-version",
    )

    assert result["status"] == "success"
    assert result["chunks_stored"] == 1
    assert result["previous_versions_found"] == 2
    assert result["previous_versions_deleted"] == 2

    assert events == [
        "store_new",
        "delete_old",
        "delete_old",
    ]

    assert pipeline.vector_store.delete_version.call_args_list == [
        call(
            tenant_id="tenant-123",
            document_id="document-123",
            version_id="old-version-1",
        ),
        call(
            tenant_id="tenant-123",
            document_id="document-123",
            version_id="old-version-2",
        ),
    ]

    pipeline.bm25_index_manager.invalidate.assert_called_once_with(
        "tenant-123"
    )


def test_zero_stored_chunks_preserves_previous_versions(setup_pipeline):
    pipeline, file_path = setup_pipeline

    pipeline.vector_store.add_documents.return_value = 0

    result = pipeline.ingest_file(
        file_path=str(file_path),
        tenant_id="tenant-123",
        document_id="document-123",
        version_id="new-version",
    )

    assert result["status"] == "skipped"
    assert result["chunks_stored"] == 0

    pipeline.vector_store.delete_version.assert_not_called()
    pipeline.bm25_index_manager.invalidate.assert_not_called()


def test_cleanup_failure_does_not_fail_new_version_ingestion(
    setup_pipeline,
):
    pipeline, file_path = setup_pipeline

    pipeline.vector_store.delete_version.side_effect = [
        RuntimeError("Simulated cleanup failure"),
        None,
    ]

    result = pipeline.ingest_file(
        file_path=str(file_path),
        tenant_id="tenant-123",
        document_id="document-123",
        version_id="new-version",
    )

    assert result["status"] == "success_with_cleanup_warning"
    assert result["chunks_stored"] == 1
    assert result["previous_versions_found"] == 2
    assert result["previous_versions_deleted"] == 1
    assert result["cleanup_errors"] == ["RuntimeError"]

    pipeline.bm25_index_manager.invalidate.assert_called_once_with(
        "tenant-123"
    )


def test_empty_chunks_preserve_previous_versions(setup_pipeline, monkeypatch):
    pipeline, file_path = setup_pipeline

    monkeypatch.setattr(
        pipeline_module,
        "chunk_documents",
        lambda documents, chunk_size, chunk_overlap: [],
    )

    result = pipeline.ingest_file(
        file_path=str(file_path),
        tenant_id="tenant-123",
        document_id="document-123",
        version_id="new-version",
    )

    assert result["status"] == "skipped"
    assert result["chunks_created"] == 0

    pipeline.embedder.embed_texts.assert_not_called()
    pipeline.vector_store.get_previous_version_ids.assert_not_called()
    pipeline.vector_store.add_documents.assert_not_called()
    pipeline.vector_store.delete_version.assert_not_called()


def test_invalid_tenant_id_is_rejected(setup_pipeline):
    pipeline, file_path = setup_pipeline

    with pytest.raises(ValueError):
        pipeline.ingest_file(
            file_path=str(file_path),
            tenant_id="",
            document_id="document-123",
            version_id="new-version",
        )

    pipeline.vector_store.add_documents.assert_not_called()
