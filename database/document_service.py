
from typing import Any
from uuid import UUID, uuid4

from database.connection import get_db_connection


class DocumentServiceError(Exception):
    """Raised when a document database operation fails."""


class DocumentService:
    """Manage tenant-scoped document and ingestion records."""

    @staticmethod
    def _validate_uuid(value: str, field_name: str) -> UUID:
        try:
            return UUID(str(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(
                f"{field_name} must be a valid UUID."
            ) from exc

    def create_document(
        self,
        organization_id: str,
        uploaded_by: str,
        source_name: str,
        file_type: str,
        storage_path: str | None = None,
        content_hash: str | None = None,
    ) -> dict[str, Any]:

        organization_uuid = self._validate_uuid(
            organization_id, "organization_id"
        )
        user_uuid = self._validate_uuid(
            uploaded_by, "uploaded_by"
        )

        source_name = source_name.strip()

        if not source_name:
            raise ValueError("Source name must not be empty.")

        if file_type not in {"pdf", "docx", "txt"}:
            raise ValueError("Unsupported document file type.")

        document_id = uuid4()
        version_id = uuid4()
        job_id = uuid4()

        try:
            with get_db_connection() as conn:

                # Serialize document registrations within this organization.
                conn.execute(
                    """
                    SELECT id
                    FROM organizations
                    WHERE id = %s
                    FOR UPDATE;
                    """,
                    (organization_uuid,),
                )

                membership = conn.execute(
                    """
                    SELECT 1
                    FROM organization_members om
                    JOIN organizations o ON o.id = om.organization_id
                    JOIN users u ON u.id = om.user_id
                    WHERE om.organization_id = %s
                      AND om.user_id = %s
                      AND o.status = 'active'
                      AND u.status = 'active';
                    """,
                    (organization_uuid, user_uuid),
                ).fetchone()

                if membership is None:
                    raise DocumentServiceError(
                        "Uploader is not an active organization member."
                    )

                existing = conn.execute(
                    """
                    SELECT id, source_name, file_type, status
                    FROM documents
                    WHERE organization_id = %s
                      AND source_name = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    FOR UPDATE;
                    """,
                    (organization_uuid, source_name),
                ).fetchone()

                if existing is not None:
                    document_id = existing[0]

                    # Prevent duplicate processing of identical content.
                    if content_hash:
                        duplicate = conn.execute(
                            """
                            SELECT dv.id, dv.version_number,
                                   dv.status, dv.chunk_count
                            FROM document_versions dv
                            WHERE dv.organization_id = %s
                              AND dv.document_id = %s
                              AND dv.content_hash = %s
                              AND dv.status = 'completed'
                            ORDER BY dv.version_number DESC
                            LIMIT 1;
                            """,
                            (
                                organization_uuid,
                                document_id,
                                content_hash,
                            ),
                        ).fetchone()

                        if duplicate is not None:
                            return {
                                "duplicate": True,
                                "document_id": str(document_id),
                                "organization_id": str(organization_uuid),
                                "source_name": existing[1],
                                "file_type": existing[2],
                                "document_status": existing[3],
                                "version_id": str(duplicate[0]),
                                "version_number": duplicate[1],
                                "version_status": duplicate[2],
                                "chunks_stored": duplicate[3],
                            }

                    version_number_row = conn.execute(
                        """
                        SELECT COALESCE(MAX(version_number), 0) + 1
                        FROM document_versions
                        WHERE organization_id = %s
                          AND document_id = %s;
                        """,
                        (organization_uuid, document_id),
                    ).fetchone()

                    version_number = version_number_row[0]

                    conn.execute(
                        """
                        UPDATE documents
                        SET uploaded_by = %s,
                            file_type = %s,
                            updated_at = NOW()
                        WHERE id = %s
                          AND organization_id = %s;
                        """,
                        (
                            user_uuid,
                            file_type,
                            document_id,
                            organization_uuid,
                        ),
                    )

                else:
                    version_number = 1

                    document = conn.execute(
                        """
                        INSERT INTO documents (
                            id, organization_id, uploaded_by,
                            source_name, file_type, status
                        )
                        VALUES (%s, %s, %s, %s, %s, 'processing')
                        RETURNING id;
                        """,
                        (
                            document_id,
                            organization_uuid,
                            user_uuid,
                            source_name,
                            file_type,
                        ),
                    ).fetchone()

                    document_id = document[0]

                version = conn.execute(
                    """
                    INSERT INTO document_versions (
                        id, organization_id, document_id,
                        version_number, storage_path, content_hash,
                        chunk_count, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 0, 'processing')
                    RETURNING id, version_number, status;
                    """,
                    (
                        version_id,
                        organization_uuid,
                        document_id,
                        version_number,
                        storage_path,
                        content_hash,
                    ),
                ).fetchone()

                job = conn.execute(
                    """
                    INSERT INTO ingestion_jobs (
                        id, organization_id, document_id,
                        version_id, status, started_at
                    )
                    VALUES (%s, %s, %s, %s, 'processing', NOW())
                    RETURNING id, status, started_at;
                    """,
                    (
                        job_id,
                        organization_uuid,
                        document_id,
                        version_id,
                    ),
                ).fetchone()

                # Mark the logical document as processing.
                conn.execute(
                    """
                    UPDATE documents
                    SET status = 'processing',
                        updated_at = NOW()
                    WHERE id = %s
                      AND organization_id = %s;
                    """,
                    (document_id, organization_uuid),
                )

            return {
                "duplicate": False,
                "document_id": str(document_id),
                "organization_id": str(organization_uuid),
                "source_name": source_name,
                "file_type": file_type,
                "document_status": "processing",
                "version_id": str(version[0]),
                "version_number": version[1],
                "version_status": version[2],
                "job_id": str(job[0]),
                "job_status": job[1],
                "started_at": job[2],
            }

        except DocumentServiceError:
            raise
        except Exception as exc:
            raise DocumentServiceError(
                "Unable to register document for ingestion."
            ) from exc

    def update_ingestion_status(
        self,
        organization_id: str,
        document_id: str,
        version_id: str,
        job_id: str,
        status: str,
        chunk_count: int = 0,
        error_message: str | None = None,
    ) -> None:

        organization_uuid = self._validate_uuid(
            organization_id, "organization_id"
        )
        document_uuid = self._validate_uuid(
            document_id, "document_id"
        )
        version_uuid = self._validate_uuid(
            version_id, "version_id"
        )
        job_uuid = self._validate_uuid(job_id, "job_id")

        if status not in {"completed", "failed"}:
            raise ValueError(
                "Final status must be completed or failed."
            )

        if chunk_count < 0:
            raise ValueError("Chunk count cannot be negative.")

        with get_db_connection() as conn:

            job = conn.execute(
                """
                UPDATE ingestion_jobs
                SET status = %s,
                    error_message = %s,
                    completed_at = NOW()
                WHERE id = %s
                  AND organization_id = %s
                  AND document_id = %s
                  AND version_id = %s
                  AND status = 'processing'
                RETURNING id;
                """,
                (
                    status,
                    error_message,
                    job_uuid,
                    organization_uuid,
                    document_uuid,
                    version_uuid,
                ),
            ).fetchone()

            if job is None:
                raise DocumentServiceError(
                    "Matching active ingestion job was not found."
                )

            conn.execute(
                """
                UPDATE document_versions
                SET status = %s,
                    chunk_count = %s
                WHERE id = %s
                  AND organization_id = %s
                  AND document_id = %s;
                """,
                (
                    status,
                    chunk_count if status == "completed" else 0,
                    version_uuid,
                    organization_uuid,
                    document_uuid,
                ),
            )

            # Keep the logical document active if another completed
            # version exists after this ingestion attempt fails.
            if status == "completed":
                document_status = "active"
            else:
                previous_completed = conn.execute(
                    """
                    SELECT 1
                    FROM document_versions
                    WHERE organization_id = %s
                      AND document_id = %s
                      AND status = 'completed'
                      AND id <> %s
                    LIMIT 1;
                    """,
                    (
                        organization_uuid,
                        document_uuid,
                        version_uuid,
                    ),
                ).fetchone()

                document_status = (
                    "active" if previous_completed else "failed"
                )

            conn.execute(
                """
                UPDATE documents
                SET status = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND organization_id = %s;
                """,
                (
                    document_status,
                    document_uuid,
                    organization_uuid,
                ),
            )
