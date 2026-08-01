import os

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    EMBEDDING_MODEL_REVISION,
    OCR_DPI,
    OCR_ENABLED,
    OCR_LANGUAGES,
    OCR_MIN_TEXT_CHARS,
)
from core.usage_events import ResourceType, UsageEvent
from document_loader import get_company, get_quarter, load_pdf_chunks
from embedding import (
    embed_passages,
    embedding_rows_to_lists,
    load_embedding_model,
)
from models.document import Document
from models.task import TaskStatus
from services.usage_service import record_usage
from storage.chroma_store import ChromaEmbeddingStore
from storage.database import SessionLocal
from storage.vector_models import VectorDocument
from tasks.repository import TaskRepository


def _set_document_status(
    db,
    *,
    document_id: int | None,
    tenant_id: int,
    status: str,
    company: str | None = None,
    period: str | None = None,
    indexed_chunk_count: int | None = None,
) -> bool:
    """Update a document only when it belongs to the task's tenant."""
    if document_id is None:
        return True

    document = db.get(Document, document_id)
    if document is None or document.tenant_id != tenant_id:
        return False

    document.status = status
    if company is not None:
        document.company = company
    if period is not None:
        document.period = period
    if indexed_chunk_count is not None:
        document.indexed_chunk_count = indexed_chunk_count
    db.commit()
    return True


def process_document_task(task_public_id: str):
    db = SessionLocal()
    repo = TaskRepository(db)
    document_id: int | None = None
    tenant_id: int | None = None
    try:
        task = repo.get_task(task_public_id)
        if task is None:
            return

        tenant_id = task.tenant_id
        if tenant_id is None:
            repo.update_task(
                task_public_id,
                status=TaskStatus.FAILED,
                error_message="tenant_id is required for document processing",
            )
            return

        payload = task.payload
        file_path = payload.get("file_path")
        document_id = payload.get("document_id")
        content_sha256 = payload.get("content_sha256")

        if document_id is not None and not _set_document_status(
            db,
            document_id=document_id,
            tenant_id=tenant_id,
            status="processing",
        ):
            repo.update_task(
                task_public_id,
                status=TaskStatus.FAILED,
                error_message="Document does not belong to this tenant",
            )
            return

        if not file_path or not os.path.exists(file_path):
            repo.update_task(
                task_public_id,
                status=TaskStatus.FAILED,
                error_message=f"File not found: {file_path}",
            )
            _set_document_status(
                db,
                document_id=document_id,
                tenant_id=tenant_id,
                status="failed",
            )
            return

        if os.path.getsize(file_path) == 0:
            raise ValueError("PDF file is empty")

        repo.update_task(task_public_id, progress=10)

        filename = os.path.basename(file_path)
        company = get_company(filename)
        quarter = get_quarter(filename)

        chunks = load_pdf_chunks(
            file_path,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
            ocr_enabled=OCR_ENABLED,
            ocr_languages=OCR_LANGUAGES,
            ocr_dpi=OCR_DPI,
            ocr_min_text_chars=OCR_MIN_TEXT_CHARS,
        )
        if not chunks:
            raise ValueError("PDF produced no indexable chunks")

        repo.update_task(task_public_id, progress=30)

        chunk_embeddings = embedding_rows_to_lists(
            embed_passages(
                load_embedding_model(),
                [chunk.text for chunk in chunks],
            )
        )
        if len(chunk_embeddings) != len(chunks):
            raise ValueError("Embedding model returned an unexpected vector count")

        repo.update_task(task_public_id, progress=50)

        store = ChromaEmbeddingStore()
        store.create_collection("financial_reports")

        doc_id = (
            f"tenant_{tenant_id}_document_{document_id}"
            if document_id is not None
            else filename.lower()
            .replace(".pdf", "")
            .replace(" ", "_")
            .replace("-", "_")
        )
        chunk_identity = (
            content_sha256
            if isinstance(content_sha256, str) and content_sha256
            else doc_id
        )
        docs = []
        for chunk, embedding in zip(
            chunks,
            chunk_embeddings,
            strict=True,
        ):
            metadata = {
                "source": filename,
                "quarter": quarter,
                "collection": "financial_reports",
                "tenant_id": tenant_id,
                "page": chunk.page,
                "section": chunk.section,
                "ocr_used": chunk.ocr_used,
                "parser_version": chunk.parser_version,
                "chunker_version": chunk.chunker_version,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_revision": EMBEDDING_MODEL_REVISION or "unversioned",
            }
            if isinstance(content_sha256, str) and content_sha256:
                metadata["content_sha256"] = content_sha256
            docs.append(
                VectorDocument(
                    document_id=doc_id,
                    chunk_id=(
                        f"tenant_{tenant_id}_{chunk_identity}_"
                        f"{chunk.chunk_index}"
                    ),
                    company=company,
                    content=chunk.text,
                    embedding=embedding,
                    metadata=metadata,
                )
            )

        repo.update_task(task_public_id, progress=80)

        # Replace this tenant-scoped document before writing. A retry after a
        # partial Chroma write cannot retain old trailing chunks when parser
        # or chunk boundaries changed.
        store.delete_document(doc_id, tenant_id=tenant_id)
        store.add_documents(docs)

        repo.update_task(
            task_public_id,
            status=TaskStatus.SUCCESS,
            progress=100,
            result={
                "chunks": len(chunks),
                "company": company,
                "document_id": document_id,
            },
        )
        _set_document_status(
            db,
            document_id=document_id,
            tenant_id=tenant_id,
            status="indexed",
            company=company,
            period=quarter,
            indexed_chunk_count=len(chunks),
        )

        record_usage(
            tenant_id=tenant_id,
            event_type=UsageEvent.DOCUMENT_PROCESS,
            resource_type=ResourceType.DOCUMENT,
            quantity=1,
            metadata={
                "task_id": task_public_id,
                "document_id": document_id,
            },
            db=db,
        )

        record_usage(
            tenant_id=tenant_id,
            event_type=UsageEvent.EMBEDDING_GENERATION,
            resource_type=ResourceType.EMBEDDING,
            quantity=len(chunks),
            metadata={
                "task_id": task_public_id,
                "chunks": len(chunks),
                "document_id": document_id,
            },
            db=db,
        )

        record_usage(
            tenant_id=tenant_id,
            event_type=UsageEvent.VECTOR_INSERT,
            resource_type=ResourceType.VECTOR,
            quantity=len(chunks),
            metadata={
                "task_id": task_public_id,
                "chunks": len(chunks),
                "document_id": document_id,
            },
            db=db,
        )

    except Exception as e:
        repo.update_task(
            task_public_id,
            status=TaskStatus.FAILED,
            error_message=str(e),
        )
        if tenant_id is not None:
            _set_document_status(
                db,
                document_id=document_id,
                tenant_id=tenant_id,
                status="failed",
            )
    finally:
        db.close()
