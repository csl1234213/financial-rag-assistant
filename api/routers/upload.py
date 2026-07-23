import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth.dependencies import get_optional_user
from core.core_engine import refresh_knowledge_base
from core.usage_events import ResourceType, UsageEvent
from models.user import User
from services.plan_service import can_upload
from services.usage_service import record_usage
from storage.database import get_db

router = APIRouter(tags=["Upload"])

UPLOAD_DIR = os.path.join("storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if current_user is not None and not can_upload(db, current_user.tenant_id):
        raise HTTPException(status_code=429, detail="Upload limit exceeded. Upgrade your plan.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    refresh_knowledge_base()

    if current_user is not None:
        record_usage(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            event_type=UsageEvent.DOCUMENT_UPLOAD,
            resource_type=ResourceType.DOCUMENT,
            quantity=1,
            metadata={"filename": file.filename},
            db=db,
        )

    return {
        "message": "upload success",
        "file": file.filename,
    }