# retrieval/hybrid_retriever.py

"""
V4 Hybrid Retriever (Retrieval Orchestrator)

Step 3: Full Refactor

Before (V3):
    retrieve(chunks, embeddings, question, company, document_ids, top_k)
    Retriever = algorithm

After (V4):
    retrieve(context, store)
    Retriever = orchestration layer
    Store = data layer
    Context = planning layer
"""

import re
from dataclasses import dataclass
from typing import Dict, List

from agent.reasoning_models import Evidence
from retrieval.document_filter import DocumentFilter
from retrieval.metadata_filter import MetadataFilter
from retrieval.retrieval_context import RetrievalContext
from storage.embedding_store import EmbeddingStore
from storage.vector_models import SearchResult

# =========================
# Data Classes
# =========================

@dataclass
class RetrievalResult:
    top_k: List
    scores: List
    chunks: List
    document_ids: List[str]
    companies: List[str]


# =========================
# Helper Functions
# =========================

def extract_keyword(query: str) -> str:
    words = re.findall(r'\w+', query.lower())
    words = [w for w in words if len(w) > 3]
    if not words:
        return query.lower()
    return max(words, key=len)


def extract_local_context(chunk: str, query: str, window: int = 2) -> str:
    keyword = extract_keyword(query)
    sentences = re.split(r'(?<=[.!?])\s+', chunk)
    hit_index = -1
    for i, sentence in enumerate(sentences):
        if keyword in sentence.lower():
            hit_index = i
            break
    if hit_index == -1:
        return chunk
    start = max(0, hit_index - window)
    end = min(len(sentences), hit_index + window + 1)
    return " ".join(sentences[start:end])


# =========================
# HybridRetriever
# =========================

class HybridRetriever:
    """
    V4 Retrieval Orchestrator

    Responsibility:
    - Interpret RetrievalContext
    - Apply filters (metadata + document)
    - Delegate vector search to EmbeddingStore
    - Post-filter and return SearchResult[]
    """

    def __init__(self, model=None):
        self.model = model
        self.metadata_filter = MetadataFilter()
        self.document_filter = DocumentFilter()

    # =========================
    # V4: New Primary Interface
    # =========================

    def retrieve(
        self,
        context: RetrievalContext,
        store: EmbeddingStore,
    ) -> List[SearchResult]:
        doc_filter = self.document_filter.build(context.document_ids)
        meta_filter = self.metadata_filter.build(
            company=context.company,
            filters=context.filters,
        )

        query_embedding = self._get_query_embedding(context.question)

        results = store.similarity_search(
            query_embedding=query_embedding,
            top_k=context.top_k,
        )

        results = self._apply_filters(results, doc_filter, meta_filter)

        return results

    # =========================
    # V4: Evidence (for Agent pipeline)
    # =========================

    def retrieve_evidence(
        self,
        context: RetrievalContext,
        store: EmbeddingStore,
    ) -> List[Evidence]:
        results = self.retrieve(context, store)

        evidences = []
        for rank, r in enumerate(results):
            local_context = extract_local_context(r.content, context.question)
            evidences.append(Evidence(
                content=local_context,
                source=r.metadata.get("source", ""),
                company=r.metadata.get("company", context.company or ""),
                confidence=round(r.score, 4),
                metadata={
                    "rank": rank + 1,
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                },
            ))
        return evidences

    # =========================
    # Internal
    # =========================

    def _get_query_embedding(self, question: str) -> List[float]:
        return self.model.encode(question, convert_to_tensor=False).tolist()

    def _apply_filters(
        self,
        results: List[SearchResult],
        doc_filter: Dict,
        meta_filter: Dict,
    ) -> List[SearchResult]:
        filtered = []

        for r in results:
            if doc_filter["document_ids"]:
                if r.document_id not in doc_filter["document_ids"]:
                    continue

            if meta_filter["company"]:
                if r.metadata.get("company") != meta_filter["company"]:
                    continue

            skip = False
            for k, v in meta_filter["filters"].items():
                if r.metadata.get(k) != v:
                    skip = True
                    break
            if skip:
                continue

            filtered.append(r)

        return filtered

    # =========================
    # V3: Legacy (backward compat)
    # =========================

    def retrieve_legacy(
        self,
        chunks,
        embeddings,
        question,
        company=None,
        document_ids=None,
        top_k=4,
    ) -> RetrievalResult:
        from sentence_transformers import util

        filtered_chunks = chunks
        if company:
            filtered_chunks = [
                c for c in filtered_chunks
                if c.get("company") == company
            ]
        if document_ids:
            filtered_chunks = [
                c for c in filtered_chunks
                if c.get("document_id") in document_ids
            ]

        question_embedding = self.model.encode(question, convert_to_tensor=True)
        scores = util.cos_sim(question_embedding, embeddings)[0]
        indexes = scores.argsort(descending=True)[:top_k]

        return RetrievalResult(
            top_k=indexes,
            scores=scores,
            chunks=chunks,
            document_ids=[
                filtered_chunks[i].get("document_id", "unknown")
                for i in indexes
                if i < len(filtered_chunks)
            ],
            companies=[company] if company else [],
        )

    def retrieve_evidence_legacy(
        self,
        chunks,
        embeddings,
        question,
        company=None,
        document_ids=None,
        top_k=4,
    ) -> List[Evidence]:
        result = self.retrieve_legacy(
            chunks=chunks,
            embeddings=embeddings,
            question=question,
            company=company,
            document_ids=document_ids,
            top_k=top_k,
        )

        evidences = []
        for rank, idx in enumerate(result.top_k):
            if idx >= len(result.chunks):
                continue
            chunk = result.chunks[idx]
            score = result.scores[idx].item() if idx < len(result.scores) else 0.0
            local_context = extract_local_context(chunk["text"], question)
            evidences.append(Evidence(
                content=local_context,
                source=chunk.get("source", ""),
                company=company or chunk.get("company", ""),
                confidence=round(score, 4),
                metadata={
                    "rank": rank + 1,
                    "chunk_id": chunk.get("chunk_id", ""),
                    "document_id": chunk.get("document_id", "unknown"),
                },
            ))
        return evidences
