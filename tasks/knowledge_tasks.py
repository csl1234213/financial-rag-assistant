import os

import fitz

from core.usage_events import ResourceType, UsageEvent
from document_loader import chunk_text, clean_text, get_company, get_quarter
from embedding import load_embedding_model
from models.task import TaskStatus
from services.usage_service import record_usage
from storage.chroma_store import ChromaEmbeddingStore
from storage.database import SessionLocal
from storage.vector_models import VectorDocument
from tasks.repository import TaskRepository


def process_document_task(task_public_id: str):
    db = SessionLocal()
    repo = TaskRepository(db)
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

        if not file_path or not os.path.exists(file_path):
            repo.update_task(
                task_public_id,
                status=TaskStatus.FAILED,
                error_message=f"File not found: {file_path}",
            )
            return

        repo.update_task(task_public_id, progress=10)

        filename = os.path.basename(file_path)
        company = get_company(filename)
        quarter = get_quarter(filename)

        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        repo.update_task(task_public_id, progress=30)

        text = clean_text(text)
        chunks = chunk_text(text)

        repo.update_task(task_public_id, progress=50)

        model = load_embedding_model()
        store = ChromaEmbeddingStore()

        store.create_collection("financial_reports")

        docs = []
        for i, chunk in enumerate(chunks):
            embedding = model.encode(chunk, convert_to_tensor=False).tolist()
            metadata = {
                "source": filename,
                "quarter": quarter,
                "collection": "financial_reports",
                "tenant_id": tenant_id,
            }
            doc_id = filename.lower().replace(".pdf", "").replace(" ", "_").replace("-", "_")
            docs.append(
                VectorDocument(
                    document_id=doc_id,
                    chunk_id=f"{doc_id}_{i}",
                    company=company,
                    content=chunk,
                    embedding=embedding,
                    metadata=metadata,
                )
            )

        repo.update_task(task_public_id, progress=80)

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
    finally:
        db.close()
