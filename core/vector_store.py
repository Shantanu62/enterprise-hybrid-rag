
import os
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models


load_dotenv()


class VectorStore:
    """Tenant-aware vector storage using Qdrant."""

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
                "QDRANT_URL and QDRANT_API_KEY must be set in .env."
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

            # Create payload indexes for tenant-aware filtering.
            for field_name in (
                "metadata.tenant_id",
                "metadata.document_id",
                "metadata.version_id",
                "metadata.source",
            ):
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )

        except Exception:
            self.client.close()
            raise

    @staticmethod
    def _validate_identifier(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must not be empty.")

        return value.strip()

    @staticmethod
    def _tenant_filter(tenant_id: str) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                )
            ]
        )

    @staticmethod
    def _document_filter(
        tenant_id: str,
        document_id: str,
    ) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
                models.FieldCondition(
                    key="metadata.document_id",
                    match=models.MatchValue(value=document_id),
                ),
            ]
        )

    @staticmethod
    def _version_filter(
        tenant_id: str,
        document_id: str,
        version_id: str,
    ) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
                models.FieldCondition(
                    key="metadata.document_id",
                    match=models.MatchValue(value=document_id),
                ),
                models.FieldCondition(
                    key="metadata.version_id",
                    match=models.MatchValue(value=version_id),
                ),
            ]
        )

    def add_documents(
        self,
        records: list[dict[str, Any]],
        vectors: list[list[float]],
        tenant_id: str,
        document_id: str,
        version_id: str,
    ) -> int:
        """Insert document chunks with mandatory tenant ownership."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )
        version_id = self._validate_identifier(
            version_id, "version_id"
        )

        if len(records) != len(vectors):
            raise ValueError(
                "The number of records must match the number of vectors."
            )

        if not records:
            return 0

        points = []
        seen_chunk_ids = set()

        for index, (record, vector) in enumerate(
            zip(records, vectors)
        ):
            if len(vector) != self.vector_size:
                raise ValueError(
                    f"Expected vector size {self.vector_size}, "
                    f"received {len(vector)}."
                )

            text = record.get("text", "")
            metadata = record.get("metadata", {})

            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    "Each record must contain non-empty text."
                )

            if not isinstance(metadata, dict):
                raise ValueError(
                    "Record metadata must be a dictionary."
                )

            metadata = metadata.copy()

            # Reject conflicting ownership information.
            existing_tenant = metadata.get("tenant_id")
            existing_document = metadata.get("document_id")
            existing_version = metadata.get("version_id")

            if existing_tenant and existing_tenant != tenant_id:
                raise ValueError(
                    "Record tenant_id does not match the requested tenant."
                )

            if existing_document and existing_document != document_id:
                raise ValueError(
                    "Record document_id does not match the requested document."
                )

            if existing_version and existing_version != version_id:
                raise ValueError(
                    "Record version_id does not match the requested version."
                )

            metadata["tenant_id"] = tenant_id
            metadata["document_id"] = document_id
            metadata["version_id"] = version_id

            chunk_index = metadata.get("chunk_index", index)

            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    (
                        f"{tenant_id}|{document_id}|"
                        f"{version_id}|{chunk_index}"
                    ),
                )
            )

            if point_id in seen_chunk_ids:
                raise ValueError(
                    "Duplicate chunk_index found in the same document version."
                )

            seen_chunk_ids.add(point_id)

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

    def search(
        self,
        query_vector: list[float],
        tenant_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search only within the authenticated tenant's data."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )

        if len(query_vector) != self.vector_size:
            raise ValueError(
                f"Expected vector size {self.vector_size}, "
                f"received {len(query_vector)}."
            )

        if limit <= 0:
            raise ValueError("limit must be greater than 0.")

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=self._tenant_filter(tenant_id),
            limit=limit,
            with_payload=True,
        )

        results = []

        for point in response.points:
            payload = point.payload or {}

            results.append(
                {
                    "id": str(point.id),
                    "text": payload.get("text", ""),
                    "metadata": payload.get("metadata", {}),
                    "score": point.score,
                }
            )

        return results

    def get_document_point_ids(
        self,
        tenant_id: str,
        document_id: str,
    ) -> list[str]:
        """Get all point IDs for one document inside one tenant."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )

        point_ids = []
        offset = None

        document_filter = self._document_filter(
            tenant_id, document_id
        )

        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=document_filter,
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            point_ids.extend(str(point.id) for point in points)

            if next_offset is None:
                break

            offset = next_offset

        return point_ids

    def get_previous_version_ids(
        self,
        tenant_id: str,
        document_id: str,
        current_version_id: str,
    ) -> list[str]:
        """Get unique previous version IDs for one tenant document."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )
        current_version_id = self._validate_identifier(
            current_version_id, "current_version_id"
        )

        previous_version_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
                models.FieldCondition(
                    key="metadata.document_id",
                    match=models.MatchValue(value=document_id),
                ),
            ],
            must_not=[
                models.FieldCondition(
                    key="metadata.version_id",
                    match=models.MatchValue(value=current_version_id),
                )
            ],
        )

        version_ids = set()
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=previous_version_filter,
                limit=100,
                offset=offset,
                with_payload=["metadata.version_id"],
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                metadata = payload.get("metadata") or {}

                if not isinstance(metadata, dict):
                    continue

                version_id = metadata.get("version_id")

                if (
                    isinstance(version_id, str)
                    and version_id.strip()
                    and version_id != current_version_id
                ):
                    version_ids.add(version_id)

            if next_offset is None:
                break

            offset = next_offset

        return sorted(version_ids)

    def get_previous_version_point_ids(
        self,
        tenant_id: str,
        document_id: str,
        current_version_id: str,
    ) -> list[str]:
        """Get point IDs from previous versions, excluding current version."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )
        current_version_id = self._validate_identifier(
            current_version_id, "current_version_id"
        )

        previous_version_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
                models.FieldCondition(
                    key="metadata.document_id",
                    match=models.MatchValue(value=document_id),
                ),
            ],
            must_not=[
                models.FieldCondition(
                    key="metadata.version_id",
                    match=models.MatchValue(value=current_version_id),
                )
            ],
        )

        point_ids = []
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=previous_version_filter,
                limit=100,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            point_ids.extend(str(point.id) for point in points)

            if next_offset is None:
                break

            offset = next_offset

        return point_ids

    def delete_version_points(
        self,
        tenant_id: str,
        document_id: str,
        version_id: str,
        point_ids: list[str],
    ) -> None:
        """Delete selected points from one specific document version."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )
        version_id = self._validate_identifier(
            version_id, "version_id"
        )

        if not point_ids:
            return

        validated_ids = [
            self._validate_identifier(point_id, "point_id")
            for point_id in point_ids
        ]

        deletion_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.tenant_id",
                    match=models.MatchValue(value=tenant_id),
                ),
                models.FieldCondition(
                    key="metadata.document_id",
                    match=models.MatchValue(value=document_id),
                ),
                models.FieldCondition(
                    key="metadata.version_id",
                    match=models.MatchValue(value=version_id),
                ),
                models.HasIdCondition(has_id=validated_ids),
            ]
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=deletion_filter
            ),
            wait=True,
        )

    def delete_version(
        self,
        tenant_id: str,
        document_id: str,
        version_id: str,
    ) -> None:
        """Delete all points belonging to one specific version."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )
        version_id = self._validate_identifier(
            version_id, "version_id"
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=self._version_filter(
                    tenant_id,
                    document_id,
                    version_id,
                )
            ),
            wait=True,
        )

    def delete_document(
        self,
        tenant_id: str,
        document_id: str,
    ) -> None:
        """Delete all versions of one document within one tenant."""

        tenant_id = self._validate_identifier(
            tenant_id, "tenant_id"
        )
        document_id = self._validate_identifier(
            document_id, "document_id"
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=self._document_filter(
                    tenant_id,
                    document_id,
                )
            ),
            wait=True,
        )

    def close(self) -> None:
        """Close the Qdrant client connection."""
        self.client.close()
