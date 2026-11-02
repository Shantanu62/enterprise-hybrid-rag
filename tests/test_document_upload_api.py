
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app
from backend.auth.dependencies import get_current_user


SAMPLE_USER = {
    "id": str(uuid4()),
    "email": "owner@example.com",
    "full_name": "Test Owner",
    "status": "active",
}

ORGANIZATION_ID = str(uuid4())

OWNER_MEMBERSHIP = {
    "user_id": SAMPLE_USER["id"],
    "email": SAMPLE_USER["email"],
    "organization_id": ORGANIZATION_ID,
    "organization_name": "Test Organization",
    "role": "owner",
}

VIEWER_MEMBERSHIP = {
    **OWNER_MEMBERSHIP,
    "role": "viewer",
}

REGISTRATION = {
    "document_id": str(uuid4()),
    "organization_id": ORGANIZATION_ID,
    "source_name": "sample.txt",
    "file_type": "txt",
    "document_status": "processing",
    "version_id": str(uuid4()),
    "version_number": 1,
    "version_status": "processing",
    "job_id": str(uuid4()),
    "job_status": "processing",
}

SUCCESSFUL_INGESTION = {
    "status": "success",
    "chunks_stored": 3,
    "previous_versions_deleted": 0,
    "message": "Ingestion completed.",
}


def setup_owner():
    app.dependency_overrides[get_current_user] = lambda: SAMPLE_USER


def test_upload_document_success():
    setup_owner()

    mock_pipeline = MagicMock()
    mock_pipeline.ingest_file.return_value = SUCCESSFUL_INGESTION

    try:
        with (
            patch(
                "backend.auth.dependencies.get_user_membership",
                return_value=OWNER_MEMBERSHIP,
            ),
            patch(
                "backend.api.routes.DocumentService"
            ) as mock_document_service,
            patch(
                "backend.api.routes.IngestionPipeline",
                return_value=mock_pipeline,
            ),
        ):
            mock_document_service.return_value.create_document.return_value = (
                REGISTRATION
            )

            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "sample.txt",
                            b"This is a test document for RAG ingestion.",
                            "text/plain",
                        )
                    },
                )

        assert response.status_code == 201

        data = response.json()

        assert data["success"] is True
        assert data["document"]["status"] == "completed"
        assert data["document"]["chunks_stored"] == 3

        mock_document_service.return_value.create_document.assert_called_once()
        mock_document_service.return_value.update_ingestion_status.assert_called_once()

        mock_pipeline.ingest_file.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_upload_without_token_returns_401():
    with TestClient(app) as client:
        response = client.post(
            f"/organizations/{ORGANIZATION_ID}/documents/upload",
            files={
                "file": ("sample.txt", b"test content", "text/plain")
            },
        )

    assert response.status_code == 401


def test_viewer_cannot_upload_document():
    setup_owner()

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=VIEWER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "sample.txt",
                            b"test content",
                            "text/plain",
                        )
                    },
                )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_non_member_cannot_upload_document():
    setup_owner()

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=None,
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "sample.txt",
                            b"test content",
                            "text/plain",
                        )
                    },
                )

        assert response.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_unsupported_file_type_returns_415():
    setup_owner()

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=OWNER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "sample.exe",
                            b"not allowed",
                            "application/octet-stream",
                        )
                    },
                )

        assert response.status_code == 415

    finally:
        app.dependency_overrides.clear()


def test_empty_file_returns_400():
    setup_owner()

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=OWNER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": ("empty.txt", b"", "text/plain")
                    },
                )

        assert response.status_code == 400

    finally:
        app.dependency_overrides.clear()


def test_file_over_10_mb_returns_413():
    setup_owner()

    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    try:
        with patch(
            "backend.auth.dependencies.get_user_membership",
            return_value=OWNER_MEMBERSHIP,
        ):
            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "large.txt",
                            oversized_content,
                            "text/plain",
                        )
                    },
                )

        assert response.status_code == 413

    finally:
        app.dependency_overrides.clear()


def test_ingestion_failure_marks_document_failed():
    setup_owner()

    mock_pipeline = MagicMock()
    mock_pipeline.ingest_file.side_effect = RuntimeError(
        "Simulated ingestion failure"
    )

    try:
        with (
            patch(
                "backend.auth.dependencies.get_user_membership",
                return_value=OWNER_MEMBERSHIP,
            ),
            patch(
                "backend.api.routes.DocumentService"
            ) as mock_document_service,
            patch(
                "backend.api.routes.IngestionPipeline",
                return_value=mock_pipeline,
            ),
        ):
            mock_document_service.return_value.create_document.return_value = (
                REGISTRATION
            )

            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "sample.txt",
                            b"Test content for failure handling.",
                            "text/plain",
                        )
                    },
                )

        assert response.status_code == 500

        mock_pipeline.vector_store.delete_version.assert_called_once()

        mock_document_service.return_value.update_ingestion_status.assert_called_once()

        failed_call = (
            mock_document_service.return_value.update_ingestion_status.call_args
        )

        assert failed_call.kwargs["status"] == "failed"

    finally:
        app.dependency_overrides.clear()


def test_ingestion_skipped_is_not_marked_completed():
    setup_owner()

    mock_pipeline = MagicMock()
    mock_pipeline.ingest_file.return_value = {
        "status": "skipped",
        "chunks_stored": 0,
        "message": "No chunks stored.",
    }

    try:
        with (
            patch(
                "backend.auth.dependencies.get_user_membership",
                return_value=OWNER_MEMBERSHIP,
            ),
            patch(
                "backend.api.routes.DocumentService"
            ) as mock_document_service,
            patch(
                "backend.api.routes.IngestionPipeline",
                return_value=mock_pipeline,
            ),
        ):
            mock_document_service.return_value.create_document.return_value = (
                REGISTRATION
            )

            with TestClient(app) as client:
                response = client.post(
                    f"/organizations/{ORGANIZATION_ID}/documents/upload",
                    files={
                        "file": (
                            "sample.txt",
                            b"Test content.",
                            "text/plain",
                        )
                    },
                )

        assert response.status_code == 500

        failed_call = (
            mock_document_service.return_value.update_ingestion_status.call_args
        )

        assert failed_call.kwargs["status"] == "failed"

    finally:
        app.dependency_overrides.clear()
