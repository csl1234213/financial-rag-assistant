import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filename = _safe_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if not can_upload(db, current_user.tenant_id):
        raise HTTPException(status_code=429, detail="Upload limit exceeded. Upgrade your plan.")

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

    document = Document(
        filename=filename,
        company=get_company(filename),
        period=get_quarter(filename),
        status="processing",
        tenant_id=current_user.tenant_id,
    )
    db.add(document)
    db.flush()

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
