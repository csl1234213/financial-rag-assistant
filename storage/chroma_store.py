from typing import List

import chromadb

from storage.embedding_store import EmbeddingStore
from storage.exceptions import EmbeddingStoreError
from storage.vector_models import SearchResult, VectorDocument


class ChromaEmbeddingStore(EmbeddingStore):
    """
    Minimal working Chroma implementation.

    Sprint 2 will add collection-targeted queries.
    """

    def __init__(self, persist_directory: str = "./chroma_db"):
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
        except Exception as e:
            raise EmbeddingStoreError(f"Failed to init Chroma: {e}")

    # =========================
    # Collection
    # =========================

    def create_collection(self, collection_name: str) -> None:
        try:
            self.client.get_or_create_collection(name=collection_name)
        except Exception as e:
            raise EmbeddingStoreError(f"Create collection failed: {e}")

    def delete_collection(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(name=collection_name)
        except Exception as e:
            raise EmbeddingStoreError(f"Delete collection failed: {e}")

    def list_collections(self) -> List[str]:
        try:
            return [c.name for c in self.client.list_collections()]
        except Exception as e:
            raise EmbeddingStoreError(f"List collections failed: {e}")

    # =========================
    # Documents
    # =========================

    def add_documents(self, documents: List[VectorDocument]) -> None:
        try:
            for doc in documents:
                collection = self.client.get_or_create_collection(
                    name=doc.metadata.get("collection", "default")
                )
                collection.add(
                    ids=[doc.chunk_id],
                    documents=[doc.content],
                    embeddings=[doc.embedding],
                    metadatas=[{
                        "document_id": doc.document_id,
                        "company": doc.company,
                        **doc.metadata,
                    }],
                )
        except Exception as e:
            raise EmbeddingStoreError(f"Add documents failed: {e}")

    # =========================
    # Query
    # =========================

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[SearchResult]:
        try:
            collections = self.client.list_collections()
            results: List[SearchResult] = []

            for c in collections:
                res = c.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                )

                if not res["ids"][0]:
                    continue

                for i in range(len(res["ids"][0])):
                    results.append(
                        SearchResult(
                            document_id=res["metadatas"][0][i]["document_id"],
                            chunk_id=res["ids"][0][i],
                            score=res["distances"][0][i],
                            content=res["documents"][0][i],
                            metadata=res["metadatas"][0][i],
                        )
                    )

            results.sort(key=lambda x: x.score)
            return results[:top_k]

        except Exception as e:
            raise EmbeddingStoreError(f"Search failed: {e}")

    # =========================
    # Utils
    # =========================

    def delete_document(self, document_id: str) -> None:
        try:
            for c in self.client.list_collections():
                c.delete(where={"document_id": document_id})
        except Exception as e:
            raise EmbeddingStoreError(f"Delete document failed: {e}")

    def count(self) -> int:
        try:
            total = 0
            for c in self.client.list_collections():
                total += c.count()
            return total
        except Exception as e:
            raise EmbeddingStoreError(f"Count failed: {e}")
