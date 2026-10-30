
import os
from uuid import NAMESPACE_URL, uuid5
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models


load_dotenv()


class VectorStore:
    """Store, search, update, and delete document embeddings using Qdrant."""

    def __init__(
        self,
        collection_name: str = "enterprise_documents",
        vector_size: int = 384,
    ) -> None:
        if vector_size <= 0:
            raise ValueError("vector_size must be greater than 0.")

        url = os.getenv("QDRANT_URL", "").strip()
        api_key = os.getenv("QDRANT_API_KEY", "").strip()

        if not url or not api_key:
            raise ValueError(
                "QDRANT_URL and QDRANT_API_KEY must be set in the .env file."
            )

        self.collection_name = collection_name
        self.vector_size = vector_size

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=30,
        )

        try:
            if not self.client.collection_exists(
                collection_name=self.collection_name
            ):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
        except Exception:
            self.client.close()
            raise

    def add_documents(
        self,
        records: list[dict[str, Any]],
        vectors: list[list[float]],
    ) -> int:
        """Insert or update document chunks using deterministic IDs."""

        if len(records) != len(vectors):
            raise ValueError(
                "The number of records must match the number of vectors."
            )

        if not records:
            return 0

        points = []

        for record, vector in zip(records, vectors):
            if len(vector) != self.vector_size:
                raise ValueError(
                    f"Expected vector size {self.vector_size}, "
                    f"received {len(vector)}."
                )

            text = record.get("text", "")
            metadata = record.get("metadata", {})

            if not isinstance(text, str) or not text.strip():
                raise ValueError("Each record must contain non-empty text.")

            if not isinstance(metadata, dict):
                raise ValueError("Record metadata must be a dictionary.")

            source = metadata.get("source", "unknown")
            page = metadata.get("page", "")
            chunk_index = metadata.get("chunk_index", "")

            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"{source}|{page}|{chunk_index}",
                )
            )

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": text,
                        "metadata": metadata,
                    },
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )

        return len(points)

    def delete_document(self, source: str) -> None:
        """Delete all chunks belonging to a document source."""

        if not isinstance(source, str) or not source.strip():
            raise ValueError("Document source must not be empty.")

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.source",
                            match=models.MatchValue(value=source),
                        )
                    ]
                )
            ),
            wait=True,
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for semantically similar document chunks."""

        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"Expected vector size {self.vector_size}, "
                f"received {len(query_vector)}."
            )

        if limit <= 0:
            raise ValueError("Search limit must be greater than 0.")

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )

        results = []

        for point in response.points:
            payload = point.payload or {}

            results.append(
                {
                    "text": payload.get("text", ""),
                    "metadata": payload.get("metadata", {}),
                    "score": point.score,
                }
            )

        return results

    def close(self) -> None:
        """Close the Qdrant client connection."""
        self.client.close()
