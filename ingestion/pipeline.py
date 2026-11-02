
from pathlib import Path
from typing import Any

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from ingestion.chunking import chunk_documents
from ingestion.loaders import load_document
from retrieval.bm25_index import BM25IndexManager


class IngestionPipeline:
    """Tenant-aware document ingestion and safe version replacement."""

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
    ) -> dict[str, Any]:
        """
        Ingest a document version for a specific tenant.

        The caller must supply verified tenant, document and version IDs.
        """

        tenant_id = self._validate_identifier(tenant_id, "tenant_id")
        document_id = self._validate_identifier(
            document_id, "document_id"
        )
        version_id = self._validate_identifier(
            version_id, "version_id"
        )

        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(
                f"Document not found: {path}"
            )

        documents = load_document(str(path))

        chunks = chunk_documents(
            documents,
            chunk_size=500,
            chunk_overlap=50,
        )

        if not chunks:
            return {
                "status": "skipped",
                "file": path.name,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "version_id": version_id,
                "documents_loaded": len(documents),
                "chunks_created": 0,
                "chunks_stored": 0,
                "old_chunks_deleted": 0,
                "message": "No text chunks were generated.",
            }

        enriched_chunks = []

        for chunk in chunks:
            enriched_chunk = chunk.copy()
            metadata = enriched_chunk.get("metadata", {}).copy()

            metadata["source"] = path.name
            enriched_chunk["metadata"] = metadata

            enriched_chunks.append(enriched_chunk)

        vectors = self.embedder.embed_texts(
            [chunk["text"] for chunk in enriched_chunks]
        )

        # Identify previous versions before inserting the new version.
        previous_version_ids = (
            self.vector_store.get_previous_version_ids(
                tenant_id=tenant_id,
                document_id=document_id,
                current_version_id=version_id,
            )
        )

        # Store the new version before removing previous versions.
        stored_count = self.vector_store.add_documents(
            records=enriched_chunks,
            vectors=vectors,
            tenant_id=tenant_id,
            document_id=document_id,
            version_id=version_id,
        )

        # A zero count means no new points were stored.
        if stored_count == 0:
            return {
                "status": "skipped",
                "file": path.name,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "version_id": version_id,
                "documents_loaded": len(documents),
                "chunks_created": len(enriched_chunks),
                "chunks_stored": 0,
                "old_chunks_deleted": 0,
                "message": "No chunks were stored. Previous versions were preserved.",
            }

        deleted_version_ids = []
        cleanup_errors = []

        # Delete only the previous versions, never the current version.
        for old_version_id in previous_version_ids:
            try:
                self.vector_store.delete_version(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    version_id=old_version_id,
                )
                deleted_version_ids.append(old_version_id)

            except Exception as exc:
                cleanup_errors.append(type(exc).__name__)

        if self.bm25_index_manager is not None:
            self.bm25_index_manager.invalidate(tenant_id)

        if cleanup_errors:
            return {
                "status": "success_with_cleanup_warning",
                "file": path.name,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "version_id": version_id,
                "documents_loaded": len(documents),
                "chunks_created": len(enriched_chunks),
                "chunks_stored": stored_count,
                "previous_versions_found": len(previous_version_ids),
                "previous_versions_deleted": len(deleted_version_ids),
                "old_chunks_deleted": None,
                "cleanup_errors": cleanup_errors,
                "message": (
                    "New version stored successfully, but some previous "
                    "versions could not be deleted."
                ),
            }

        return {
            "status": "success",
            "file": path.name,
            "tenant_id": tenant_id,
            "document_id": document_id,
            "version_id": version_id,
            "documents_loaded": len(documents),
            "chunks_created": len(enriched_chunks),
            "chunks_stored": stored_count,
            "previous_versions_found": len(previous_version_ids),
            "previous_versions_deleted": len(deleted_version_ids),
            "message": (
                "Tenant-scoped document ingestion and version replacement "
                "completed successfully."
            ),
        }

    def close(self) -> None:
        """Release the Qdrant client connection."""
        self.vector_store.close()
