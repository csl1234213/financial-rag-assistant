from abc import ABC, abstractmethod
from typing import List

from storage.vector_models import (
    SearchResult,
    VectorDocument,
)


class EmbeddingStore(ABC):
    """
    Abstract interface for all vector databases.

    Future implementations:
    - ChromaDB
    - Qdrant
    - Milvus
    - Pinecone
    - PGVector
    """

    @abstractmethod
    def create_collection(self, collection_name: str) -> None:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        pass

    @abstractmethod
    def add_documents(self, documents: List[VectorDocument]) -> None:
        pass

    @abstractmethod
    def similarity_search(
        self,
        query_embedding,
        top_k: int = 5,
    ) -> List[SearchResult]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass
