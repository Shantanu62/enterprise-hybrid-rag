
from uuid import uuid4

import pytest

from database.connection import get_db_connection
from database.document_service import (
    DocumentService,
    DocumentServiceError,
)


@pytest.fixture
def service():
    return DocumentService()


@pytest.fixture
def active_owner():
    """Get an existing active organization owner for testing."""

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT
                u.id,
                o.id
            FROM users u
            JOIN organization_members om ON om.user_id = u.id
            JOIN organizations o ON o.id = om.organization_id
            WHERE u.status = 'active'
              AND o.status = 'active'
              AND om.role = 'owner'
            LIMIT 1;
            """
        ).fetchone()

    if row is None:
        pytest.skip("No active organization owner found.")

    return {
        "user_id": str(row[0]),
        "organization_id": str(row[1]),
    }


def test_create_document_success(service, active_owner):
    result = service.create_document(
        organization_id=active_owner["organization_id"],
        uploaded_by=active_owner["user_id"],
        source_name="document_service_test.txt",
        file_type="txt",
        storage_path="test/document_service_test.txt",
        content_hash="test-hash-123",
    )

    assert result["document_id"]
    assert result["version_id"]
    assert result["job_id"]
    assert result["document_status"] == "processing"
    assert result["version_status"] == "processing"
    assert result["job_status"] == "processing"

    try:
        service.update_ingestion_status(
            organization_id=active_owner["organization_id"],
            document_id=result["document_id"],
            version_id=result["version_id"],
            job_id=result["job_id"],
            status="completed",
            chunk_count=3,
        )

        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    d.status,
                    dv.status,
                    dv.chunk_count,
                    ij.status
                FROM documents d
                JOIN document_versions dv
                    ON dv.document_id = d.id
                   AND dv.organization_id = d.organization_id
                JOIN ingestion_jobs ij
                    ON ij.document_id = d.id
                   AND ij.version_id = dv.id
                   AND ij.organization_id = d.organization_id
                WHERE d.id = %s
                  AND d.organization_id = %s;
                """,
                (
                    result["document_id"],
                    active_owner["organization_id"],
                ),
            ).fetchone()

        assert row is not None
        assert row[0] == "active"
        assert row[1] == "completed"
        assert row[2] == 3
        assert row[3] == "completed"

    finally:
        with get_db_connection() as conn:
            conn.execute(
                """
                DELETE FROM documents
                WHERE id = %s
                  AND organization_id = %s;
                """,
                (
                    result["document_id"],
                    active_owner["organization_id"],
                ),
            )


def test_create_document_rejects_non_member(service, active_owner):
    random_user_id = str(uuid4())

    with pytest.raises(
        DocumentServiceError,
        match="not an active organization member",
    ):
        service.create_document(
            organization_id=active_owner["organization_id"],
            uploaded_by=random_user_id,
            source_name="unauthorized_test.txt",
            file_type="txt",
        )


def test_create_document_rejects_invalid_file_type(
    service,
    active_owner,
):
    with pytest.raises(ValueError, match="Unsupported"):
        service.create_document(
            organization_id=active_owner["organization_id"],
            uploaded_by=active_owner["user_id"],
            source_name="invalid_test.exe",
            file_type="exe",
        )


def test_update_rejects_invalid_final_status(service, active_owner):
    with pytest.raises(ValueError, match="Final status"):
        service.update_ingestion_status(
            organization_id=active_owner["organization_id"],
            document_id=str(uuid4()),
            version_id=str(uuid4()),
            job_id=str(uuid4()),
            status="processing",
        )
