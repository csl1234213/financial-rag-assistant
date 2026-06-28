import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import shutil
import uuid

import pytest

from storage.chroma_store import ChromaEmbeddingStore
from storage.vector_models import SearchResult, VectorDocument


@pytest.fixture
def store():
    db_dir = f"./chroma_db_test_{uuid.uuid4().hex[:8]}"
    s = ChromaEmbeddingStore(persist_directory=db_dir)
    yield s
    shutil.rmtree(db_dir, ignore_errors=True)


class TestChromaEmbeddingStore:
    def test_create_collection(self, store):
        store.create_collection("test_collection")
        assert "test_collection" in store.list_collections()

    def test_delete_collection(self, store):
        store.create_collection("test_collection")
        store.delete_collection("test_collection")
        assert "test_collection" not in store.list_collections()

    def test_list_collections_empty(self, store):
        cols = store.list_collections()
        assert isinstance(cols, list)

    def test_count_empty(self, store):
        assert store.count() == 0

    def test_add_and_count(self, store):
        store.create_collection("default")
        doc = VectorDocument(
            document_id="test_doc",
            chunk_id="test_doc_0",
            company="Apple",
            content="Revenue grew 10% year over year.",
            embedding=[0.1] * 384,
            metadata={"collection": "default", "source": "test.pdf"},
        )
        store.add_documents([doc])
        assert store.count() == 1

    def test_add_multiple_documents(self, store):
        store.create_collection("default")
        docs = []
        for i in range(5):
            docs.append(VectorDocument(
                document_id=f"doc_{i}",
                chunk_id=f"doc_{i}_0",
                company="Test",
                content=f"Content {i}",
                embedding=[0.1] * 384,
                metadata={"collection": "default"},
            ))
        store.add_documents(docs)
        assert store.count() == 5

    def test_similarity_search(self, store):
        store.create_collection("default")
        store.add_documents([
            VectorDocument(
                document_id="doc_a",
                chunk_id="doc_a_0",
                company="Apple",
                content="Apple revenue grew 10%.",
                embedding=[0.5] * 384,
                metadata={"collection": "default", "source": "apple.pdf"},
            ),
            VectorDocument(
                document_id="doc_b",
                chunk_id="doc_b_0",
                company="NVIDIA",
                content="NVIDIA data center revenue up 50%.",
                embedding=[0.1] * 384,
                metadata={"collection": "default", "source": "nvidia.pdf"},
            ),
        ])
        results = store.similarity_search([0.5] * 384, top_k=2)
        assert len(results) >= 1
        assert isinstance(results[0], SearchResult)
        assert results[0].document_id is not None
        assert results[0].chunk_id is not None
        assert results[0].score is not None
        assert results[0].content is not None

    def test_similarity_search_top_k(self, store):
        store.create_collection("default")
        for i in range(10):
            store.add_documents([
                VectorDocument(
                    document_id=f"doc_{i}",
                    chunk_id=f"doc_{i}_0",
                    company="Test",
                    content=f"Content {i}",
                    embedding=[0.1] * 384,
                    metadata={"collection": "default"},
                )
            ])
        results = store.similarity_search([0.5] * 384, top_k=3)
        assert len(results) <= 3

    def test_delete_document(self, store):
        store.create_collection("default")
        store.add_documents([
            VectorDocument(
                document_id="to_delete",
                chunk_id="to_delete_0",
                company="Test",
                content="This will be deleted.",
                embedding=[0.1] * 384,
                metadata={"collection": "default"},
            )
        ])
        assert store.count() == 1
        store.delete_document("to_delete")
        assert store.count() == 0

    def test_similarity_search_empty(self, store):
        results = store.similarity_search([0.5] * 384)
        assert len(results) == 0
