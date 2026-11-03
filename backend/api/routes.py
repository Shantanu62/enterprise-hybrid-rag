
import hashlib
import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from backend.auth.dependencies import require_org_permission
from database.connection import get_db_connection
from database.document_service import DocumentService
from ingestion.pipeline import IngestionPipeline
from retrieval.rag_service import RAGService


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Organization Access"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = PROJECT_ROOT / "data" / "uploads"

MAX_UPLOAD_SIZE = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
}


class AskRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )


def resolve_source_names(
    organization_id: UUID,
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve original document filenames from PostgreSQL."""

    if not sources:
        return sources

    document_ids = set()

    for source in sources:
        raw_document_id = source.get("document_id")

        if not raw_document_id:
            continue

        try:
            document_ids.add(UUID(str(raw_document_id)))
        except (ValueError, TypeError, AttributeError):
            logger.warning(
                "Invalid document ID found in RAG source metadata."
            )

    if not document_ids:
        return sources

    ordered_ids = sorted(document_ids, key=str)
    placeholders = ", ".join(["%s"] * len(ordered_ids))

    query = f"""
        SELECT id, source_name
        FROM documents
        WHERE organization_id = %s
          AND id IN ({placeholders})
    """

    try:
        with get_db_connection() as connection:
            rows = connection.execute(
                query,
                (organization_id, *ordered_ids),
            ).fetchall()

        filename_map = {
            str(row[0]): row[1]
            for row in rows
            if row[0] is not None and row[1]
        }

        resolved_sources = []

        for source in sources:
            resolved_source = dict(source)

            raw_document_id = resolved_source.get("document_id")

            if raw_document_id:
                try:
                    document_id = str(UUID(str(raw_document_id)))

                    original_filename = filename_map.get(
                        document_id
                    )

                    if original_filename:
                        resolved_source["source"] = original_filename

                except (ValueError, TypeError, AttributeError):
                    pass

            resolved_sources.append(resolved_source)

        return resolved_sources

    except Exception:
        logger.exception(
            "Could not resolve original filenames for RAG citations."
        )
        return sources


@router.get("/organizations/{organization_id}/access-check")
def check_organization_access(
    organization_id: UUID,
    access: dict[str, Any] = Depends(
        require_org_permission("organization:read")
    ),
):
    user = access["user"]
    membership = access["membership"]

    return {
        "success": True,
        "message": "Organization access verified successfully.",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
        },
        "organization": {
            "id": membership["organization_id"],
            "name": membership["organization_name"],
            "role": membership["role"],
        },
    }


@router.get("/organizations/{organization_id}/admin-check")
def check_admin_access(
    organization_id: UUID,
    access: dict[str, Any] = Depends(
        require_org_permission("members:invite")
    ),
):
    membership = access["membership"]

    return {
        "success": True,
        "message": "Member management permission verified.",
        "organization_id": membership["organization_id"],
        "role": membership["role"],
    }


@router.post(
    "/organizations/{organization_id}/documents/upload",
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
)
async def upload_document(
    organization_id: UUID,
    response: Response,
    file: UploadFile = File(...),
    access: dict[str, Any] = Depends(
        require_org_permission("documents:upload")
    ),
):
    """Upload and ingest a document for an authorized organization."""

    organization_id = access["organization_id"]
    uploaded_by = access["user"]["id"]

    original_filename = (file.filename or "").replace("\\", "/")
    source_name = original_filename.split("/")[-1].strip()

    if not source_name:
        raise HTTPException(
            status_code=400,
            detail="A valid filename is required.",
        )

    extension = Path(source_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Allowed formats: PDF, DOCX, TXT.",
        )

    file_type = ALLOWED_EXTENSIONS[extension]

    organization_directory = UPLOAD_ROOT / str(organization_id)
    storage_filename = f"{uuid4().hex}{extension}"
    storage_path = organization_directory / storage_filename

    relative_storage_path = (
        Path("data")
        / "uploads"
        / str(organization_id)
        / storage_filename
    )

    file_size = 0
    content_hasher = hashlib.sha256()

    document_service = DocumentService()
    pipeline = None
    registration = None

    try:
        organization_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        with storage_path.open("wb") as destination:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)

                if not chunk:
                    break

                file_size += len(chunk)

                if file_size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the maximum allowed size of 10 MB.",
                    )

                content_hasher.update(chunk)
                destination.write(chunk)

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        content_hash = content_hasher.hexdigest()

        registration = document_service.create_document(
            organization_id=organization_id,
            uploaded_by=uploaded_by,
            source_name=source_name,
            file_type=file_type,
            storage_path=str(relative_storage_path),
            content_hash=content_hash,
        )

        if registration.get("duplicate"):
            storage_path.unlink(missing_ok=True)
            response.status_code = status.HTTP_200_OK

            return {
                "success": True,
                "duplicate": True,
                "message": (
                    "This document with identical content has already "
                    "been uploaded."
                ),
                "document": {
                    "document_id": registration["document_id"],
                    "version_id": registration["version_id"],
                    "organization_id": registration["organization_id"],
                    "source_name": registration["source_name"],
                    "file_type": registration["file_type"],
                    "status": registration["document_status"],
                    "version_number": registration["version_number"],
                    "chunks_stored": registration["chunks_stored"],
                },
            }

        pipeline = IngestionPipeline()

        ingestion_result = pipeline.ingest_file(
            file_path=str(storage_path),
            tenant_id=str(organization_id),
            document_id=str(registration["document_id"]),
            version_id=str(registration["version_id"]),
            source_name=source_name,
        )

        if ingestion_result.get("status") != "success":
            raise RuntimeError(
                "Document ingestion did not store any chunks."
            )

        chunk_count = ingestion_result.get("chunks_stored", 0)

        if not isinstance(chunk_count, int) or chunk_count <= 0:
            raise RuntimeError(
                "Ingestion returned an invalid stored chunk count."
            )

        document_service.update_ingestion_status(
            organization_id=organization_id,
            document_id=registration["document_id"],
            version_id=registration["version_id"],
            job_id=registration["job_id"],
            status="completed",
            chunk_count=chunk_count,
        )

        cleanup_result = pipeline.cleanup_previous_versions(
            tenant_id=str(organization_id),
            document_id=str(registration["document_id"]),
            version_ids=ingestion_result.get(
                "previous_version_ids", []
            ),
        )

        cleanup_warning = not cleanup_result["success"]

        return {
            "success": True,
            "duplicate": False,
            "message": (
                "Document uploaded and ingested successfully."
                if not cleanup_warning
                else (
                    "Document ingested successfully, but some previous "
                    "version points could not be deleted."
                )
            ),
            "document": {
                "document_id": registration["document_id"],
                "version_id": registration["version_id"],
                "job_id": registration["job_id"],
                "organization_id": str(organization_id),
                "source_name": source_name,
                "file_type": file_type,
                "file_size_bytes": file_size,
                "content_hash": content_hash,
                "status": "completed",
                "version_number": registration["version_number"],
                "chunks_stored": chunk_count,
            },
            "ingestion": {
                "status": (
                    "success_with_cleanup_warning"
                    if cleanup_warning
                    else "success"
                ),
                "message": ingestion_result.get("message"),
                "previous_versions_found": ingestion_result.get(
                    "previous_versions_found", 0
                ),
                "previous_versions_deleted": cleanup_result[
                    "previous_versions_deleted"
                ],
                "previous_versions_remaining": cleanup_result[
                    "previous_versions_remaining"
                ],
                "cleanup_errors": cleanup_result["cleanup_errors"],
            },
        }

    except HTTPException:
        storage_path.unlink(missing_ok=True)
        raise

    except Exception as exc:
        logger.exception("Document upload or ingestion failed.")

        if registration is not None and pipeline is not None:
            try:
                pipeline.vector_store.delete_version(
                    tenant_id=str(organization_id),
                    document_id=str(registration["document_id"]),
                    version_id=str(registration["version_id"]),
                )
            except Exception:
                logger.exception(
                    "Could not clean up partially stored Qdrant points."
                )

        if (
            registration is not None
            and registration.get("job_id")
            and registration.get("version_id")
        ):
            try:
                document_service.update_ingestion_status(
                    organization_id=organization_id,
                    document_id=registration["document_id"],
                    version_id=registration["version_id"],
                    job_id=registration["job_id"],
                    status="failed",
                    error_message=type(exc).__name__,
                )
            except Exception:
                logger.exception(
                    "Could not update failed ingestion status."
                )

        storage_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Document upload or ingestion failed. Check server logs.",
        ) from exc

    finally:
        await file.close()

        if pipeline is not None:
            try:
                pipeline.close()
            except Exception:
                logger.exception(
                    "Could not close ingestion pipeline resources."
                )


@router.post(
    "/organizations/{organization_id}/ask",
    tags=["RAG"],
)
def ask_organization_documents(
    organization_id: UUID,
    request: AskRequest,
    access: dict[str, Any] = Depends(
        require_org_permission("search:execute")
    ),
):
    """Answer a question using the authenticated organization's documents."""

    verified_organization_id = access["organization_id"]
    rag_service = None

    try:
        rag_service = RAGService()

        result = rag_service.answer(
            question=request.question,
            tenant_id=verified_organization_id,
        )

        original_sources = result.get("sources", [])

        # Resolve original filenames using organization-scoped PostgreSQL data.
        sources = resolve_source_names(
            organization_id=verified_organization_id,
            sources=original_sources,
        )

        # Replace hashed filenames in the generated answer with original names.
        answer = result["answer"]

        for original_source, resolved_source in zip(
            original_sources,
            sources,
        ):
            old_filename = original_source.get("source")
            original_filename = resolved_source.get("source")

            if (
                old_filename
                and original_filename
                and old_filename != original_filename
            ):
                answer = answer.replace(
                    str(old_filename),
                    str(original_filename),
                )

        return {
            "success": True,
            "organization_id": verified_organization_id,
            "question": result["question"],
            "answer": answer,
            "sources": sources,
            "model": result["model"],
            "performance": result["performance"],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Organization RAG request failed.")

        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer. Check server logs.",
        ) from exc

    finally:
        if rag_service is not None:
            try:
                rag_service.close()
            except Exception:
                logger.exception(
                    "Could not close RAG service resources."
                )
