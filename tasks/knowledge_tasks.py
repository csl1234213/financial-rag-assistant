import os
from dataclasses import replace
from pathlib import Path

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
from core.financial_table_rows import (
    financial_table_rows_from_chunk,
    financial_table_rows_json,
)
from core.usage_events import ResourceType, UsageEvent
from document_loader import (
    get_company,
    get_document_company,
    get_document_period,
    get_quarter,
    load_document_chunks,
    load_pdf_chunks,
)
from embedding import (
    embed_passages,
    embedding_rows_to_lists,
    load_embedding_model,
)
from models.document import Document
from models.task import TaskStatus
from retrieval.periods import extract_metrics, extract_periods
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
            message = "PDF file is empty" if Path(file_path).suffix.casefold() == ".pdf" else "Document file is empty"
            raise ValueError(message)

        repo.update_task(task_public_id, progress=10)

        filename = os.path.basename(file_path)
        filename_company_hint = get_company(filename)
        filename_period_hint = get_quarter(filename)
        doc_id = (
            f"tenant_{tenant_id}_document_{document_id}"
            if document_id is not None
            else Path(filename).stem.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        if Path(filename).suffix.casefold() == ".pdf":
            chunks = load_pdf_chunks(
                file_path,
                chunk_size=CHUNK_SIZE,
                overlap=CHUNK_OVERLAP,
                ocr_enabled=OCR_ENABLED,
                ocr_languages=OCR_LANGUAGES,
                ocr_dpi=OCR_DPI,
                ocr_min_text_chars=OCR_MIN_TEXT_CHARS,
                document_id=doc_id,
            )
        else:
            chunks = load_document_chunks(
                file_path,
                chunk_size=CHUNK_SIZE,
                overlap=CHUNK_OVERLAP,
            )
        if not chunks:
            message = (
                "PDF produced no indexable chunks"
                if Path(filename).suffix.casefold() == ".pdf"
                else "Document produced no indexable chunks"
            )
            raise ValueError(message)

        # Filing scope must be supported by opening document content. A name
        # or Q-number in the upload filename is kept only as diagnostic metadata.
        company = get_document_company(chunks, filename_hint=filename_company_hint)
        quarter = get_document_period(chunks)

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
                "filename_company_hint": filename_company_hint,
                "filename_period_hint": filename_period_hint,
                "periods": "|".join(extract_periods(chunk.text)),
                "metrics": "|".join(extract_metrics(chunk.text)),
                "collection": "financial_reports",
                "tenant_id": tenant_id,
                "section": chunk.section,
                "ocr_used": chunk.ocr_used,
                "parser_version": chunk.parser_version,
                "chunker_version": chunk.chunker_version,
                "table_context": chunk.table_context or "",
                "source_locator": chunk.source_locator or "",
                "page_label": chunk.source_locator or "",
                "content_type": chunk.content_type,
                "source_format": chunk.source_format,
                "source_authority": "tenant_upload",
                "embedding_model": EMBEDDING_MODEL,
                "embedding_revision": EMBEDDING_MODEL_REVISION or "unversioned",
            }
            financial_rows = tuple(
                replace(
                    row,
                    document_id=doc_id,
                    company=company,
                    source=filename,
                )
                for row in chunk.financial_table_rows
            ) or financial_table_rows_from_chunk(
                content=chunk.text,
                content_type=chunk.content_type,
                document_id=doc_id,
                company=company,
                section=chunk.section,
                table_context=chunk.table_context or "",
                page=chunk.page,
                source=filename,
                source_locator=chunk.source_locator or "",
            )
            if financial_rows:
                # Chroma metadata accepts scalar values; serialize the typed
                # candidates without flattening away period, scope, or audit
                # status. P1.5 will consume only VERIFIED rows as facts.
                metadata["financial_table_rows_json"] = financial_table_rows_json(
                    financial_rows
                )
            if chunk.page > 0:
                metadata["page"] = chunk.page
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
