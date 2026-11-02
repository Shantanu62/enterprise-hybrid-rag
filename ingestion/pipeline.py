
from pathlib import Path
from typing import Any

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from ingestion.chunking import chunk_documents
from ingestion.loaders import load_document
from retrieval.bm25_index import BM25IndexManager


class IngestionPipeline:
    """Tenant-aware document ingestion with safe version replacement."""

    def __init__(
        self,
        bm25_index_manager: BM25IndexManager | None = None,
    ) -> None:
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()
        self.bm25_index_manager = bm25_index_manager

    @staticmethod
    def _validate_identifier(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must not be empty.")
        return value.strip()

    def ingest_file(
        self,
        file_path: str,
        tenant_id: str,
        document_id: str,
        version_id: str,
        source_name: str | None = None,
    ) -> dict[str, Any]:

        tenant_id = self._validate_identifier(tenant_id, "tenant_id")
        document_id = self._validate_identifier(document_id, "document_id")
        version_id = self._validate_identifier(version_id, "version_id")

        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Document not found: {path}")

        original_source = (source_name or path.name).strip()
        if not original_source:
            raise ValueError("Source name must not be empty.")

        documents = load_document(str(path))

        chunks = chunk_documents(
            documents,
            chunk_size=500,
            chunk_overlap=50,
        )

        if not chunks:
            return {
                "status": "skipped",
                "file": original_source,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "version_id": version_id,
                "documents_loaded": len(documents),
                "chunks_created": 0,
                "chunks_stored": 0,
                "previous_version_ids": [],
                "previous_versions_found": 0,
                "message": "No text chunks were generated.",
            }

        enriched_chunks = []

        for chunk in chunks:
            enriched_chunk = chunk.copy()
            metadata = enriched_chunk.get("metadata", {}).copy()

            metadata["source"] = original_source

            enriched_chunk["metadata"] = metadata
            enriched_chunks.append(enriched_chunk)

        vectors = self.embedder.embed_texts(
            [chunk["text"] for chunk in enriched_chunks]
        )

        previous_version_ids = (
            self.vector_store.get_previous_version_ids(
                tenant_id=tenant_id,
                document_id=document_id,
                current_version_id=version_id,
            )
        )

        stored_count = self.vector_store.add_documents(
            records=enriched_chunks,
            vectors=vectors,
            tenant_id=tenant_id,
            document_id=document_id,
            version_id=version_id,
        )

        if stored_count == 0:
            return {
                "status": "skipped",
                "file": original_source,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "version_id": version_id,
                "documents_loaded": len(documents),
                "chunks_created": len(enriched_chunks),
                "chunks_stored": 0,
                "previous_version_ids": [],
                "previous_versions_found": 0,
                "message": (
                    "No chunks were stored. Previous versions were preserved."
                ),
            }

        if self.bm25_index_manager is not None:
            self.bm25_index_manager.invalidate(tenant_id)

        return {
            "status": "success",
            "file": original_source,
            "tenant_id": tenant_id,
            "document_id": document_id,
            "version_id": version_id,
            "documents_loaded": len(documents),
            "chunks_created": len(enriched_chunks),
            "chunks_stored": stored_count,
            "previous_version_ids": previous_version_ids,
            "previous_versions_found": len(previous_version_ids),
            "previous_versions_deleted": 0,
            "message": (
                "New version stored successfully. Previous versions "
                "are preserved until database completion is confirmed."
            ),
        }

    def cleanup_previous_versions(
        self,
        tenant_id: str,
        document_id: str,
        version_ids: list[str],
    ) -> dict[str, Any]:
        """Delete old versions only after the new version is completed."""

        deleted_version_ids = []
        cleanup_errors = []

        for old_version_id in version_ids:
            try:
                self.vector_store.delete_version(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    version_id=old_version_id,
                )
                deleted_version_ids.append(old_version_id)

            except Exception as exc:
                cleanup_errors.append({
                    "version_id": old_version_id,
                    "error": type(exc).__name__,
                })

        if self.bm25_index_manager is not None:
            self.bm25_index_manager.invalidate(tenant_id)

        return {
            "previous_versions_deleted": len(deleted_version_ids),
            "previous_versions_remaining": (
                len(version_ids) - len(deleted_version_ids)
            ),
            "cleanup_errors": cleanup_errors,
            "success": not cleanup_errors,
        }

    def close(self) -> None:
        """Release the Qdrant client connection."""
        self.vector_store.close()
