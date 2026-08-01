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

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List

from agent.reasoning_models import Evidence
from embedding import embed_query
from retrieval.bm25_retriever import BM25Retriever
from retrieval.document_filter import DocumentFilter
from retrieval.metadata_filter import MetadataFilter
from retrieval.query_enrichment import enrich_financial_query
from retrieval.retrieval_context import RetrievalContext
from storage.embedding_store import EmbeddingStore
from storage.vector_models import SearchResult

logger = logging.getLogger(__name__)

_ENRICHED_QUERY_LEXICAL_WEIGHT_MULTIPLIER = 2.0

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


@dataclass(frozen=True)
class HybridRetrievalConfig:
    """Configuration for deterministic reciprocal-rank fusion."""

    enabled: bool = True
    vector_weight: float = 1.0
    lexical_weight: float = 1.0
    rrf_k: int = 60
    candidate_multiplier: int = 4

    def __post_init__(self) -> None:
        if self.vector_weight < 0 or self.lexical_weight < 0:
            raise ValueError("hybrid retrieval weights cannot be negative")
        if self.vector_weight + self.lexical_weight <= 0:
            raise ValueError("at least one hybrid retrieval weight must be positive")
        if self.rrf_k < 1:
            raise ValueError("rrf_k must be at least 1")
        if self.candidate_multiplier < 1:
            raise ValueError("candidate_multiplier must be at least 1")


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

    def __init__(
        self,
        model=None,
        *,
        config: HybridRetrievalConfig | None = None,
        lexical_retriever: BM25Retriever | None = None,
    ):
        self.model = model
        self._model_lock = Lock()
        self.metadata_filter = MetadataFilter()
        self.document_filter = DocumentFilter()
        self.config = config or HybridRetrievalConfig()
        self.lexical_retriever = lexical_retriever or BM25Retriever()

    # =========================
    # V4: New Primary Interface
    # =========================

    def retrieve(
        self,
        context: RetrievalContext,
        store: EmbeddingStore,
    ) -> List[SearchResult]:
        if context.top_k <= 0:
            return []

        doc_filter = self.document_filter.build(context.document_ids)
        meta_filter = self.metadata_filter.build(
            company=context.company,
            filters=context.filters,
        )

        retrieval_query = enrich_financial_query(
            context.question,
            context.company,
        )
        query_embedding = self._get_query_embedding(retrieval_query)
        candidate_k = context.top_k * self.config.candidate_multiplier
        tenant_scopes = [context.tenant_id]
        if context.include_public and context.tenant_id != 0:
            tenant_scopes.append(0)

        vector_results: list[SearchResult] = []
        for tenant_id in tenant_scopes:
            scoped_results = store.similarity_search(
                query_embedding=query_embedding,
                top_k=candidate_k,
                tenant_id=tenant_id,
            )
            scoped_results = self._apply_tenant_scope(scoped_results, tenant_id)
            vector_results.extend(
                self._apply_filters(scoped_results, doc_filter, meta_filter)
            )

        # Merge independently ranked tenant scopes only when the store exposes
        # score direction. Legacy stores without semantics retain their stable
        # best-first ordering.
        vector_results = self._deduplicate(
            self._globally_rank_vector_results(vector_results)
        )[:candidate_k]

        if not self.config.enabled or self.config.lexical_weight == 0:
            return vector_results[: context.top_k]

        lexical_corpus = self._load_lexical_corpus(
            store=store,
            tenant_scopes=tenant_scopes,
            doc_filter=doc_filter,
            meta_filter=meta_filter,
        )
        if not lexical_corpus:
            return vector_results[: context.top_k]

        lexical_results = self.lexical_retriever.search(
            query=retrieval_query,
            documents=lexical_corpus,
            top_k=candidate_k,
        )
        if not lexical_results:
            return vector_results[: context.top_k]

        return self._reciprocal_rank_fusion(
            vector_results,
            lexical_results,
            top_k=context.top_k,
            lexical_weight=(
                self.config.lexical_weight
                * _ENRICHED_QUERY_LEXICAL_WEIGHT_MULTIPLIER
                if retrieval_query != context.question
                else self.config.lexical_weight
            ),
        )

    @staticmethod
    def _merge_ranked_results(
        primary: List[SearchResult],
        secondary: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """Merge tenant and public results without duplicate chunks."""
        return HybridRetriever._deduplicate([*primary, *secondary])[:top_k]

    def _load_lexical_corpus(
        self,
        *,
        store: EmbeddingStore,
        tenant_scopes: list[int],
        doc_filter: Dict,
        meta_filter: Dict,
    ) -> list[SearchResult] | None:
        corpus_loader = getattr(store, "lexical_corpus", None)
        if not callable(corpus_loader):
            return None

        corpus: list[SearchResult] = []
        try:
            for tenant_id in tenant_scopes:
                scoped_documents = corpus_loader(tenant_id=tenant_id)
                scoped_documents = self._apply_tenant_scope(
                    scoped_documents,
                    tenant_id,
                )
                corpus.extend(
                    self._apply_filters(
                        scoped_documents,
                        doc_filter,
                        meta_filter,
                    )
                )
        except Exception:
            logger.warning(
                "Lexical corpus unavailable; using vector-only retrieval",
                exc_info=True,
            )
            return None

        return self._deduplicate(
            sorted(
                corpus,
                key=lambda item: (item.document_id, item.chunk_id),
            )
        )

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[SearchResult],
        lexical_results: list[SearchResult],
        *,
        top_k: int,
        lexical_weight: float | None = None,
    ) -> list[SearchResult]:
        effective_lexical_weight = (
            self.config.lexical_weight
            if lexical_weight is None
            else lexical_weight
        )
        records: dict[tuple[str, str], SearchResult] = {}
        fused_scores: dict[tuple[str, str], float] = {}
        vector_ranks: dict[tuple[str, str], int] = {}
        lexical_ranks: dict[tuple[str, str], int] = {}

        for rank, result in enumerate(vector_results, start=1):
            key = self._result_key(result)
            records.setdefault(key, result)
            vector_ranks.setdefault(key, rank)
            fused_scores[key] = fused_scores.get(key, 0.0) + (
                self.config.vector_weight / (self.config.rrf_k + rank)
            )

        for rank, result in enumerate(lexical_results, start=1):
            key = self._result_key(result)
            records.setdefault(key, result)
            lexical_ranks.setdefault(key, rank)
            fused_scores[key] = fused_scores.get(key, 0.0) + (
                effective_lexical_weight / (self.config.rrf_k + rank)
            )

        missing_rank = len(records) + 1
        ordered_keys = sorted(
            records,
            key=lambda key: (
                -fused_scores[key],
                vector_ranks.get(key, missing_rank),
                lexical_ranks.get(key, missing_rank),
                key,
            ),
        )
        maximum_score = (
            self.config.vector_weight + effective_lexical_weight
        ) / (self.config.rrf_k + 1)
        lexical_by_key = {
            self._result_key(result): result
            for result in lexical_results
        }

        fused: list[SearchResult] = []
        for key in ordered_keys[:top_k]:
            result = records[key]
            metadata = dict(result.metadata)
            lexical_result = lexical_by_key.get(key)
            metadata.update(
                {
                    "retrieval_strategy": "hybrid_rrf",
                    "score_semantics": "relevance",
                    "rrf_score": fused_scores[key],
                    "vector_rank": vector_ranks.get(key),
                    "bm25_rank": lexical_ranks.get(key),
                    "bm25_score": (
                        lexical_result.metadata.get("bm25_score")
                        if lexical_result is not None
                        else None
                    ),
                    "lexical_weight": effective_lexical_weight,
                }
            )
            fused.append(
                SearchResult(
                    document_id=result.document_id,
                    chunk_id=result.chunk_id,
                    score=round(fused_scores[key] / maximum_score, 6),
                    content=result.content,
                    metadata=metadata,
                )
            )
        return fused

    @staticmethod
    def _result_key(result: SearchResult) -> tuple[str, str]:
        normalized_content = re.sub(
            r"\s+",
            " ",
            unicodedata.normalize("NFKC", result.content),
        ).strip().casefold()
        return (
            result.document_id,
            normalized_content or result.chunk_id,
        )

    @staticmethod
    def _deduplicate(results: List[SearchResult]) -> List[SearchResult]:
        deduplicated: List[SearchResult] = []
        seen: set[tuple[str, str]] = set()
        for result in results:
            key = HybridRetriever._result_key(result)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(result)
        return deduplicated

    @staticmethod
    def _globally_rank_vector_results(
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """Merge private/public candidates using explicit score semantics.

        Chroma returns each tenant scope in best-first distance order. Merely
        concatenating those lists permanently favored the private scope even
        when a public candidate was substantially closer. Explicit distance,
        similarity, and relevance scores are converted to one relevance
        direction. Legacy results without score semantics keep their original
        stable ordering because their numeric direction is unknowable.
        """

        ranked: list[tuple[int, SearchResult, float | None]] = [
            (
                index,
                result,
                HybridRetriever._vector_relevance(result),
            )
            for index, result in enumerate(results)
        ]
        if not any(relevance is not None for _, _, relevance in ranked):
            return list(results)

        ranked.sort(
            key=lambda item: (
                item[2] is None,
                -(item[2] if item[2] is not None else 0.0),
                item[0],
            )
        )
        return [result for _, result, _ in ranked]

    @staticmethod
    def _vector_relevance(result: SearchResult) -> float | None:
        for field in ("similarity_score", "confidence"):
            value = result.metadata.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)

        semantics = result.metadata.get("score_semantics")
        score = float(result.score)
        if semantics == "distance":
            return 1.0 / (1.0 + max(score, 0.0))
        if semantics in {"similarity", "relevance"}:
            return score
        return None

    @staticmethod
    def _apply_tenant_scope(
        results: List[SearchResult],
        tenant_id: int,
    ) -> List[SearchResult]:
        """Reject a result if its explicit tenant metadata crosses scope."""
        scoped: list[SearchResult] = []
        for result in results:
            result_tenant = result.metadata.get("tenant_id")
            if result_tenant is not None and result_tenant != tenant_id:
                continue
            scoped.append(result)
        return scoped

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
            evidence_metadata = {
                "rank": rank + 1,
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
            }
            for field in (
                "retrieval_strategy",
                "rrf_score",
                "vector_rank",
                "bm25_rank",
                "bm25_score",
                "page",
                "section",
                "ocr_used",
                "parser_version",
                "chunker_version",
                "embedding_model",
                "embedding_revision",
                "content_sha256",
            ):
                value = r.metadata.get(field)
                if value is not None:
                    evidence_metadata[field] = value
            evidences.append(Evidence(
                content=local_context,
                source=r.metadata.get("source", ""),
                company=r.metadata.get("company", context.company or ""),
                confidence=self._evidence_confidence(r),
                metadata=evidence_metadata,
            ))
        return evidences

    @staticmethod
    def _evidence_confidence(result: SearchResult) -> float:
        """Normalize explicit distance/similarity fields to relevance."""
        for field in ("similarity_score", "confidence"):
            value = result.metadata.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return round(min(max(float(value), 0.0), 1.0), 4)

        score = float(result.score)
        semantics = result.metadata.get("score_semantics")
        if semantics == "distance":
            relevance = 1.0 / (1.0 + max(score, 0.0))
        elif semantics in {"relevance", "similarity"}:
            relevance = score
        else:
            # Backward compatibility: historical in-memory stores used score
            # as confidence and did not attach a semantics marker.
            relevance = score
        return round(min(max(relevance, 0.0), 1.0), 4)

    # =========================
    # Internal
    # =========================

    def _get_query_embedding(self, question: str) -> List[float]:
        # A single embedding model is shared across API requests and across
        # the bounded parallel retrieval workers. Model inference is guarded;
        # vector-store requests can still run concurrently after encoding.
        with self._model_lock:
            return embed_query(
                self.model,
                question,
                convert_to_tensor=False,
            ).tolist()

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

        question_embedding = embed_query(
            self.model,
            question,
            convert_to_tensor=True,
        )
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
