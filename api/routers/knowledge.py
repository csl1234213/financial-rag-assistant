import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from models.document import Document
from models.task import Task, TaskStatus, TaskType
from models.user import User
from storage.chroma_store import ChromaEmbeddingStore
from storage.database import get_db

router = APIRouter(tags=["Knowledge"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "storage/uploads"))


def _document_item(
    document: Document,
    *,
    current_user_id: int,
) -> dict[str, object]:
    return {
        "id": document.id,
        "filename": document.filename,
        "company": document.company,
        "period": document.period,
        "status": document.status,
        "chunk_count": document.indexed_chunk_count or 0,
        "byte_size": document.byte_size,
        "content_sha256": document.content_sha256,
        "uploaded_at": document.created_at,
        "can_delete": document.uploaded_by_user_id == current_user_id,
    }


def _document_tasks(
    db: Session,
    *,
    tenant_id: int,
    document_id: int,
) -> list[Task]:
    candidates = (
        db.query(Task)
        .filter(
            Task.tenant_id == tenant_id,
            Task.task_type == TaskType.PROCESS_DOCUMENT.value,
        )
        .all()
    )
    return [
        task
        for task in candidates
        if task.payload.get("document_id") == document_id
    ]


def _upload_directories(*, tenant_id: int, document_id: int) -> list[Path]:
    """Resolve only the upload directories owned by one document.

    The directory layout is ``UPLOAD_DIR/<tenant>/<document-id>-<uuid>``.
    Every resolved target must remain an immediate child of the tenant root,
    preventing a malformed task path or symlink from widening deletion scope.
    """

    tenant_root = (UPLOAD_DIR / str(tenant_id)).resolve()
    if not tenant_root.is_dir():
        return []

    directories: list[Path] = []
    for candidate in tenant_root.glob(f"{document_id}-*"):
        resolved = candidate.resolve()
        if (
            candidate.is_dir()
            and not candidate.is_symlink()
            and resolved.parent == tenant_root
            and resolved.name.startswith(f"{document_id}-")
        ):
            directories.append(resolved)
    return sorted(directories)


def _stage_upload_directories(
    directories: list[Path],
    *,
    tenant_id: int,
    document_id: int,
) -> list[tuple[Path, Path]]:
    tenant_root = (UPLOAD_DIR / str(tenant_id)).resolve()
    staged: list[tuple[Path, Path]] = []
    try:
        for original in directories:
            staged_path = tenant_root / (
                f".deleting-{document_id}-{uuid.uuid4().hex}"
            )
            original.rename(staged_path)
            staged.append((original, staged_path))
    except OSError:
        _restore_upload_directories(staged)
        raise
    return staged


def _restore_upload_directories(staged: list[tuple[Path, Path]]) -> None:
    for original, staged_path in reversed(staged):
        if staged_path.exists() and not original.exists():
            staged_path.rename(original)


def _remove_staged_upload_directories(
    staged: list[tuple[Path, Path]],
    *,
    tenant_id: int,
) -> None:
    tenant_root = (UPLOAD_DIR / str(tenant_id)).resolve()
    for _, staged_path in staged:
        resolved = staged_path.resolve()
        if (
            staged_path.is_dir()
            and not staged_path.is_symlink()
            and resolved.parent == tenant_root
            and resolved.name.startswith(".deleting-")
        ):
            shutil.rmtree(resolved)


@router.get("/knowledge")
def knowledge_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .all()
    )
    return {
        # Keep the legacy filename list while clients transition to stable
        # document IDs in ``items``.
        "documents": [document.filename for document in docs],
        "items": [
            _document_item(
                document,
                current_user_id=current_user.id,
            )
            for document in docs
        ],
        "document_count": len(docs),
        "companies": sorted(
            {document.company for document in docs if document.company}
        ),
    }


@router.get("/knowledge/statistics")
def knowledge_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(Document)
        .filter(Document.tenant_id == current_user.tenant_id)
        .all()
    )
    chunk_count = sum(document.indexed_chunk_count or 0 for document in docs)
    return {
        "documents": len(docs),
        "companies": len(
            {document.company for document in docs if document.company}
        ),
        "chunks": chunk_count,
        "embeddings": chunk_count,
    }


@router.delete("/knowledge/{document_id}")
def delete_knowledge_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if document is None:
        # The same response is used for absent and foreign-tenant IDs.
        raise HTTPException(status_code=404, detail="Document not found")

    if (
        document.uploaded_by_user_id is None
        or document.uploaded_by_user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this document.",
        )

    document_tasks = _document_tasks(
        db,
        tenant_id=current_user.tenant_id,
        document_id=document.id,
    )
    has_active_task = any(
        task.status
        in {
            TaskStatus.PENDING.value,
            TaskStatus.RUNNING.value,
        }
        for task in document_tasks
    )
    if document.status == "processing" or has_active_task:
        raise HTTPException(
            status_code=409,
            detail="Document is still processing and cannot be deleted.",
        )

    directories = _upload_directories(
        tenant_id=current_user.tenant_id,
        document_id=document.id,
    )
    try:
        staged = _stage_upload_directories(
            directories,
            tenant_id=current_user.tenant_id,
            document_id=document.id,
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to prepare document storage for deletion.",
        ) from exc

    vector_document_id = (
        f"tenant_{current_user.tenant_id}_document_{document.id}"
    )
    try:
        with ChromaEmbeddingStore() as store:
            store.delete_document(
                vector_document_id,
                tenant_id=current_user.tenant_id,
            )
    except Exception as exc:
        try:
            _restore_upload_directories(staged)
        except OSError:
            logger.exception(
                "Failed to restore upload directory after vector delete error"
            )
        raise HTTPException(
            status_code=503,
            detail="Unable to delete document vectors.",
        ) from exc

    try:
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        try:
            _restore_upload_directories(staged)
        except OSError:
            logger.exception(
                "Failed to restore upload directory after database error"
            )
        raise

    try:
        _remove_staged_upload_directories(
            staged,
            tenant_id=current_user.tenant_id,
        )
    except OSError:
        logger.exception(
            "Document metadata was deleted but staged file cleanup failed",
            extra={
                "tenant_id": current_user.tenant_id,
                "document_id": document_id,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Document was deleted but storage cleanup is pending.",
        )

    return {
        "deleted": True,
        "document_id": document_id,
    }
