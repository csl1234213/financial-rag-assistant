from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock

import fitz
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import tasks.knowledge_tasks as knowledge_tasks
from models.document import Document
from models.task import TaskStatus, TaskType
from models.tenant import Tenant
from models.user import User
from storage.database import Base, _import_models
from tasks.repository import TaskRepository


@dataclass(frozen=True)
class ProcessingTask:
    public_id: str
    document_id: int


@pytest.fixture
def task_database(monkeypatch):
    _import_models()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    db = session_factory()

    tenant = Tenant(name="Knowledge Task Tenant", slug="knowledge-task")
    db.add(tenant)
    db.flush()
    user = User(
        email="knowledge-task@example.com",
        password_hash="test-hash",
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()

    monkeypatch.setattr(knowledge_tasks, "SessionLocal", session_factory)
    embedding_loader = Mock(
        side_effect=AssertionError("invalid documents must fail before loading the embedding model")
    )
    store_factory = Mock(side_effect=AssertionError("invalid documents must fail before opening the vector store"))
    usage_recorder = Mock()
    monkeypatch.setattr(
        knowledge_tasks,
        "load_embedding_model",
        embedding_loader,
    )
    monkeypatch.setattr(
        knowledge_tasks,
        "ChromaEmbeddingStore",
        store_factory,
    )
    monkeypatch.setattr(knowledge_tasks, "record_usage", usage_recorder)

    def create_processing_task(
        pdf_path: Path,
        *,
        content_sha256: str | None = None,
    ) -> ProcessingTask:
        document = Document(
            filename=pdf_path.name,
            company="Tesla",
            report_type="Financial Report",
            period="Unknown",
            status="processing",
            tenant_id=tenant.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        task = TaskRepository(db).create_task(
            TaskType.PROCESS_DOCUMENT,
            {
                "file_path": str(pdf_path),
                "document_id": document.id,
                **({"content_sha256": content_sha256} if content_sha256 is not None else {}),
            },
            tenant.id,
            user.id,
        )
        return ProcessingTask(
            public_id=task.public_id,
            document_id=document.id,
        )

    yield db, create_processing_task, embedding_loader, store_factory, usage_recorder

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _assert_processing_failed(
    db: Session,
    processing_task: ProcessingTask,
    expected_error: str,
) -> None:
    db.expire_all()
    task = TaskRepository(db).get_task(processing_task.public_id)
    document = db.get(Document, processing_task.document_id)

    assert task is not None
    assert task.status == TaskStatus.FAILED.value
    assert task.error_message == expected_error
    assert task.result == {}
    assert document is not None
    assert document.status == "failed"


def test_empty_pdf_fails_before_embedding(
    tmp_path,
    task_database,
):
    db, create_task, embedding_loader, store_factory, usage_recorder = task_database
    pdf_path = tmp_path / "tesla-empty.pdf"
    pdf_path.write_bytes(b"")
    processing_task = create_task(pdf_path)

    knowledge_tasks.process_document_task(processing_task.public_id)

    _assert_processing_failed(
        db,
        processing_task,
        "PDF file is empty",
    )
    embedding_loader.assert_not_called()
    store_factory.assert_not_called()
    usage_recorder.assert_not_called()


def test_zero_page_pdf_is_not_marked_indexed(
    tmp_path,
    task_database,
):
    db, create_task, embedding_loader, store_factory, usage_recorder = task_database
    pdf_path = tmp_path / "tesla-zero-pages.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )
    processing_task = create_task(pdf_path)

    knowledge_tasks.process_document_task(processing_task.public_id)

    _assert_processing_failed(
        db,
        processing_task,
        "PDF contains no pages",
    )
    embedding_loader.assert_not_called()
    store_factory.assert_not_called()
    usage_recorder.assert_not_called()


def test_pdf_without_extractable_text_is_not_marked_indexed(
    tmp_path,
    task_database,
):
    db, create_task, embedding_loader, store_factory, usage_recorder = task_database
    pdf_path = tmp_path / "tesla-blank-page.pdf"
    with fitz.open() as document:
        document.new_page()
        document.save(pdf_path)
    processing_task = create_task(pdf_path)

    knowledge_tasks.process_document_task(processing_task.public_id)

    _assert_processing_failed(
        db,
        processing_task,
        "PDF contains no extractable text",
    )
    embedding_loader.assert_not_called()
    store_factory.assert_not_called()
    usage_recorder.assert_not_called()


def test_zero_generated_chunks_is_not_marked_indexed(
    monkeypatch,
    tmp_path,
    task_database,
):
    db, create_task, embedding_loader, store_factory, usage_recorder = task_database
    pdf_path = tmp_path / "tesla-text-without-chunks.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Tesla revenue comparison for 2024 and 2025.")
        document.save(pdf_path)
    processing_task = create_task(pdf_path)
    monkeypatch.setattr(
        knowledge_tasks,
        "load_pdf_chunks",
        lambda *_args, **_kwargs: [],
    )

    knowledge_tasks.process_document_task(processing_task.public_id)

    _assert_processing_failed(
        db,
        processing_task,
        "PDF produced no indexable chunks",
    )
    embedding_loader.assert_not_called()
    store_factory.assert_not_called()
    usage_recorder.assert_not_called()


def test_successful_processing_batches_embeddings_and_persists_provenance(
    tmp_path,
    task_database,
):
    db, create_task, embedding_loader, store_factory, usage_recorder = task_database
    pdf_path = tmp_path / "Tesla_Q2_2025.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Revenue Overview", fontsize=16)
        page.insert_text(
            (72, 160),
            "Tesla automotive revenue increased during the quarter.",
        )
        document.save(pdf_path)

    content_sha256 = "a" * 64
    processing_task = create_task(
        pdf_path,
        content_sha256=content_sha256,
    )
    model = Mock()
    model.encode.return_value = [[0.1, 0.2, 0.3]]
    embedding_loader.side_effect = None
    embedding_loader.return_value = model
    store = Mock()
    store_factory.side_effect = None
    store_factory.return_value = store

    knowledge_tasks.process_document_task(processing_task.public_id)

    db.expire_all()
    task = TaskRepository(db).get_task(processing_task.public_id)
    document = db.get(Document, processing_task.document_id)
    assert task is not None
    assert task.status == TaskStatus.SUCCESS.value
    assert document is not None
    assert document.status == "indexed"
    assert document.indexed_chunk_count == 1

    encode_call = model.encode.call_args
    assert encode_call.args[0][0].startswith("passage: ")
    assert encode_call.kwargs["normalize_embeddings"] is True
    assert encode_call.kwargs["batch_size"] > 0

    inserted = store.add_documents.call_args.args[0]
    assert len(inserted) == 1
    vector_document = inserted[0]
    store.delete_document.assert_called_once_with(
        vector_document.document_id,
        tenant_id=document.tenant_id,
    )
    assert vector_document.chunk_id == (f"tenant_{document.tenant_id}_{content_sha256}_0")
    assert vector_document.metadata["page"] == 1
    assert vector_document.metadata["section"] == "Revenue Overview"
    assert vector_document.metadata["ocr_used"] is False
    assert vector_document.metadata["parser_version"]
    assert vector_document.metadata["chunker_version"]
    assert vector_document.metadata["embedding_model"] == ("intfloat/multilingual-e5-small")
    assert vector_document.metadata["content_sha256"] == content_sha256
    assert usage_recorder.call_count == 3
