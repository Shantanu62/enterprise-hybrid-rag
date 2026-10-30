
from pathlib import Path
from typing import Any

from core.embeddings import EmbeddingService
from core.vector_store import VectorStore
from ingestion.chunking import chunk_documents
from ingestion.loaders import load_document


class IngestionPipeline:
    """Load, chunk, embed, and store documents in Qdrant Cloud."""

    def __init__(self) -> None:
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()

    def ingest_file(self, file_path: str) -> dict[str, Any]:
        """Ingest a document and replace its previous chunks safely."""

        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Document not found: {path}")

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
                "documents_loaded": len(documents),
                "chunks_created": 0,
                "chunks_stored": 0,
                "message": "No text chunks were generated.",
            }

        vectors = self.embedder.embed_texts(
            [chunk["text"] for chunk in chunks]
        )

        # Validate and prepare all new points before deleting old chunks.
        # This avoids deleting the existing document if embedding fails.
        source = path.name

        # Replace previous chunks belonging to this filename.
        self.vector_store.delete_document(source)

        try:
            stored_count = self.vector_store.add_documents(
                chunks,
                vectors,
            )
        except Exception:
            raise

        return {
            "status": "success",
            "file": path.name,
            "documents_loaded": len(documents),
            "chunks_created": len(chunks),
            "chunks_stored": stored_count,
            "message": "Document ingestion completed successfully.",
        }

    def close(self) -> None:
        """Release the Qdrant client connection."""
        self.vector_store.close()
