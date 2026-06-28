import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.core_engine import refresh_knowledge_base

router = APIRouter(tags=["Upload"])

UPLOAD_DIR = os.path.join("storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    refresh_knowledge_base()

    return {
        "message": "upload success",
        "file": file.filename,
    }
