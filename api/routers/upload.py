import hashlib
import os
import uuid
from pathlib import Path

import fitz
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from core.usage_events import ResourceType, UsageEvent
from document_loader import get_company, get_quarter
from models.document import Document
from models.task import TaskType
from models.user import User
from services.plan_service import can_upload
from services.usage_service import record_usage
from storage.database import get_db
from tasks.broker import get_broker
from tasks.repository import TaskRepository

router = APIRouter(tags=["Upload"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "storage/uploads"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
PDF_HEADER = b"%PDF-"
PDF_EOF_MARKER = b"%%EOF"
DUPLICATE_DOCUMENT_DETAIL = "This document already exists in your workspace."


def _safe_filename(filename: str | None) -> str:
    """Return a basename only, so uploads cannot escape their tenant directory."""
    candidate = Path((filename or "").replace("\\", "/")).name
    if not candidate or candidate in {".", ".."}:
        raise HTTPException(status_code=400, detail="A valid filename is required")
    return candidate


def _has_pdf_signature(content: bytes) -> bool:
    """Perform a bounded structural signature check before persistence."""

    return (
        content.startswith(PDF_HEADER)
        and PDF_EOF_MARKER in content[-1024:]
    )


def _validate_pdf_structure(content: bytes) -> None:
    """Reject unreadable, encrypted, and zero-page PDFs before persistence.

    This is intentionally a lightweight container check. Text extraction,
    chunking, OCR, and embedding remain asynchronous worker responsibilities.
    """

    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            if document.needs_pass or document.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Encrypted PDF documents are not supported",
                )
            if document.page_count < 1:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded PDF must contain at least one page",
                )
    except HTTPException:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF could not be opened",
        ) from exc


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = _safe_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit",
        )
    if not _has_pdf_signature(content):
        raise HTTPException(
            status_code=400,
            detail="Uploaded content is not a valid PDF document",
        )
    _validate_pdf_structure(content)

    content_sha256 = hashlib.sha256(content).hexdigest()
    existing_document = (
        db.query(Document)
        .filter(
            Document.tenant_id == current_user.tenant_id,
            Document.content_sha256 == content_sha256,
        )
        .first()
    )
    if existing_document is not None:
        raise HTTPException(status_code=409, detail=DUPLICATE_DOCUMENT_DETAIL)

    if not can_upload(db, current_user.tenant_id):
        raise HTTPException(status_code=429, detail="Upload limit exceeded. Upgrade your plan.")

    document = Document(
        filename=filename,
        company=get_company(filename),
        period=get_quarter(filename),
        status="processing",
        tenant_id=current_user.tenant_id,
        content_sha256=content_sha256,
        byte_size=len(content),
        uploaded_by_user_id=current_user.id,
        indexed_chunk_count=0,
    )
    db.add(document)
    try:
        db.flush()
    except IntegrityError:
        # The database constraint is authoritative for concurrent requests.
        # Re-check only the authenticated tenant before classifying the
        # integrity error, so another tenant's document is never disclosed.
        db.rollback()
        duplicate = (
            db.query(Document.id)
            .filter(
                Document.tenant_id == current_user.tenant_id,
                Document.content_sha256 == content_sha256,
            )
            .first()
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail=DUPLICATE_DOCUMENT_DETAIL,
            )
        raise

    upload_directory = (
        UPLOAD_DIR
        / str(current_user.tenant_id)
        / f"{document.id}-{uuid.uuid4().hex}"
    )
    file_path = upload_directory / filename

    try:
        upload_directory.mkdir(parents=True, exist_ok=False)
        file_path.write_bytes(content)

        task = TaskRepository(db).create_task(
            task_type=TaskType.PROCESS_DOCUMENT,
            payload={
                "file_path": str(file_path),
                "document_id": document.id,
                "content_sha256": content_sha256,
            },
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
    except OSError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to persist uploaded file") from exc

    broker = get_broker()
    if broker.enabled:
        broker.publish_task(task.public_id, current_user.tenant_id, task.task_type)

    record_usage(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        event_type=UsageEvent.DOCUMENT_UPLOAD,
        resource_type=ResourceType.DOCUMENT,
        quantity=1,
        metadata={"filename": filename, "document_id": document.id, "task_id": task.public_id},
        db=db,
    )

    return {
        "message": "upload success",
        "file": filename,
        "document_id": document.id,
        "task_id": task.public_id,
        "status": task.status,
    }
