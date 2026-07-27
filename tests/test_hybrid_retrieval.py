from __future__ import annotations

from collections.abc import Sequence

from core.retrieval_tool_adapter import TenantRetrievalToolExecutor
from evaluation.metrics import ranked_retrieval_metrics
from retrieval.hybrid_retriever import (
    HybridRetrievalConfig,
    HybridRetriever,
)
from retrieval.retrieval_context import RetrievalContext
from storage.chroma_store import ChromaEmbeddingStore
from storage.vector_models import SearchResult, VectorDocument


class _Embedding(list):
    def tolist(self):
        return list(self)


class _EmbeddingModel:
    def encode(self, _question, convert_to_tensor=False):
        return _Embedding([0.1, 0.2])


class _HybridStore:
    def __init__(
        self,
        *,
        vectors: dict[int, Sequence[SearchResult]],
        corpora: dict[int, Sequence[SearchResult]],
        lexical_error: bool = False,
    ):
        self.vectors = vectors
        self.corpora = corpora
        self.lexical_error = lexical_error
        self.vector_calls: list[tuple[int | None, int]] = []
        self.lexical_calls: list[int | None] = []

    def similarity_search(self, *, query_embedding, top_k, tenant_id):
        self.vector_calls.append((tenant_id, top_k))
        return list(self.vectors.get(tenant_id, ()))[:top_k]

    def lexical_corpus(self, tenant_id=None):
        self.lexical_calls.append(tenant_id)
        if self.lexical_error:
            raise RuntimeError("lexical index unavailable")
        return list(self.corpora.get(tenant_id, ()))


class _VectorOnlyStore:
    def __init__(self, results: Sequence[SearchResult]):
        self.results = list(results)

    def similarity_search(self, *, query_embedding, top_k, tenant_id):
        return self.results[:top_k]


def _result(
    document_id: str,
    chunk_id: str,
    score: float,
    content: str,
    *,
    tenant_id: int = 7,
    company: str = "Tesla",
    **metadata,
) -> SearchResult:
    return SearchResult(
        document_id=document_id,
        chunk_id=chunk_id,
        score=score,
        content=content,
        metadata={
            "tenant_id": tenant_id,
            "company": company,
            "source": f"{document_id}.pdf",
            **metadata,
        },
    )


def test_hybrid_rrf_combines_vector_and_bm25_ranks():
    generic = _result("generic", "generic-1", 0.01, "General business outlook.")
    revenue = _result(
        "tesla-q2",
        "tesla-revenue",
        0.20,
        "Tesla automotive revenue growth accelerated in the quarter.",
    )
    margins = _result(
        "tesla-q2",
        "tesla-margin",
        0.30,
        "Tesla revenue growth supported automotive margins.",
    )
    store = _HybridStore(
        vectors={7: [generic, revenue, margins]},
        corpora={7: [generic, revenue, margins]},
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(
            question="Tesla revenue growth accelerated",
            tenant_id=7,
            top_k=3,
        ),
        store,
    )

    assert [result.chunk_id for result in results] == [
        "tesla-revenue",
        "tesla-margin",
        "generic-1",
    ]
    assert results[0].metadata["retrieval_strategy"] == "hybrid_rrf"
    assert results[0].metadata["vector_rank"] == 2
    assert results[0].metadata["bm25_rank"] == 1
    assert store.vector_calls == [(7, 12)]
    assert store.lexical_calls == [7]


def test_evidence_normalizes_explicit_distance_and_similarity_scores():
    distance = _result(
        "distance",
        "distance-1",
        0.25,
        "Distance-based revenue evidence.",
        score_semantics="distance",
    )
    similarity = _result(
        "similarity",
        "similarity-1",
        0.10,
        "Similarity-based revenue evidence.",
        similarity_score=0.91,
    )
    retriever = HybridRetriever(
        _EmbeddingModel(),
        config=HybridRetrievalConfig(enabled=False),
    )

    distance_evidence = retriever.retrieve_evidence(
        RetrievalContext(question="revenue", tenant_id=7),
        _VectorOnlyStore([distance]),
    )
    similarity_evidence = retriever.retrieve_evidence(
        RetrievalContext(question="revenue", tenant_id=7),
        _VectorOnlyStore([similarity]),
    )

    assert distance_evidence[0].confidence == 0.8
    assert similarity_evidence[0].confidence == 0.91


def test_hybrid_deduplicates_stably_across_channels():
    duplicate = _result(
        "tesla-q2",
        "tesla-revenue",
        0.10,
        "Tesla revenue growth was 20 percent.",
    )
    other = _result(
        "tesla-q2",
        "tesla-cash",
        0.20,
        "Tesla cash flow improved.",
    )
    store = _HybridStore(
        vectors={7: [duplicate, duplicate, other]},
        corpora={7: [duplicate, duplicate, other]},
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(
            question="Tesla revenue growth",
            tenant_id=7,
            top_k=3,
        ),
        store,
    )

    assert [result.chunk_id for result in results] == [
        "tesla-revenue",
        "tesla-cash",
    ]


def test_hybrid_applies_tenant_company_document_and_metadata_filters():
    allowed = _result(
        "allowed",
        "allowed-1",
        0.20,
        "Tesla revenue growth in fiscal 2025.",
        year="2025",
    )
    wrong_tenant = _result(
        "foreign",
        "foreign-1",
        0.01,
        "Tesla revenue growth in fiscal 2025.",
        tenant_id=99,
        year="2025",
    )
    wrong_company = _result(
        "apple",
        "apple-1",
        0.02,
        "Apple revenue growth in fiscal 2025.",
        company="Apple",
        year="2025",
    )
    wrong_year = _result(
        "legacy",
        "legacy-1",
        0.03,
        "Tesla revenue growth in fiscal 2024.",
        year="2024",
    )
    candidates = [wrong_tenant, wrong_company, wrong_year, allowed]
    store = _HybridStore(
        vectors={7: candidates},
        corpora={7: candidates},
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(
            question="Tesla revenue growth",
            tenant_id=7,
            company="Tesla",
            document_ids=["allowed"],
            filters={"year": "2025"},
        ),
        store,
    )

    assert [result.chunk_id for result in results] == ["allowed-1"]
    assert store.vector_calls[0][0] == 7
    assert store.lexical_calls == [7]


def test_hybrid_queries_only_private_and_explicit_public_lexical_scopes():
    private = _result(
        "private",
        "private-1",
        0.10,
        "Tesla revenue growth from private evidence.",
    )
    public = _result(
        "public",
        "public-1",
        0.20,
        "Tesla revenue growth from public evidence.",
        tenant_id=0,
    )
    foreign = _result(
        "foreign",
        "foreign-1",
        0.01,
        "Tesla revenue growth from another tenant.",
        tenant_id=99,
    )
    store = _HybridStore(
        vectors={7: [private], 0: [public], 99: [foreign]},
        corpora={7: [private], 0: [public], 99: [foreign]},
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(
            question="Tesla revenue growth",
            tenant_id=7,
            include_public=True,
        ),
        store,
    )

    assert {result.chunk_id for result in results} == {"private-1", "public-1"}
    assert [tenant_id for tenant_id, _ in store.vector_calls] == [7, 0]
    assert store.lexical_calls == [7, 0]


def test_missing_lexical_capability_preserves_vector_only_result():
    vector_result = _result(
        "vector",
        "vector-1",
        0.17,
        "Semantic evidence without a lexical provider.",
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(question="revenue", tenant_id=7),
        _VectorOnlyStore([vector_result]),
    )

    assert results == [vector_result]
    assert results[0].score == 0.17
    assert "retrieval_strategy" not in results[0].metadata


def test_lexical_failure_preserves_vector_only_result():
    vector_result = _result(
        "vector",
        "vector-1",
        0.17,
        "Semantic revenue evidence.",
    )
    store = _HybridStore(
        vectors={7: [vector_result]},
        corpora={},
        lexical_error=True,
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(question="revenue", tenant_id=7),
        store,
    )

    assert results == [vector_result]


def test_hybrid_weights_are_configurable():
    vector_first = _result(
        "semantic",
        "semantic-1",
        0.01,
        "General performance discussion.",
    )
    lexical_only = _result(
        "lexical",
        "lexical-1",
        0.20,
        "Rareterm exact identifier match.",
    )
    store = _HybridStore(
        vectors={7: [vector_first]},
        corpora={7: [vector_first, lexical_only]},
    )
    retriever = HybridRetriever(
        _EmbeddingModel(),
        config=HybridRetrievalConfig(
            vector_weight=2.0,
            lexical_weight=1.0,
        ),
    )

    results = retriever.retrieve(
        RetrievalContext(question="rareterm", tenant_id=7, top_k=2),
        store,
    )

    assert [result.chunk_id for result in results] == [
        "semantic-1",
        "lexical-1",
    ]


def test_hybrid_golden_sample_reports_ranked_retrieval_metrics():
    generic = _result("generic", "generic-1", 0.01, "General outlook.")
    revenue = _result(
        "tesla-q2",
        "gold-revenue",
        0.20,
        "Tesla revenue growth accelerated.",
    )
    margin = _result(
        "tesla-q2",
        "gold-margin",
        0.30,
        "Tesla revenue growth improved margins.",
    )
    store = _HybridStore(
        vectors={7: [generic, revenue, margin]},
        corpora={7: [generic, revenue, margin]},
    )

    results = HybridRetriever(_EmbeddingModel()).retrieve(
        RetrievalContext(
            question="Tesla revenue growth",
            tenant_id=7,
            top_k=3,
        ),
        store,
    )
    metrics = ranked_retrieval_metrics(
        [result.chunk_id for result in results],
        ["gold-revenue", "gold-margin"],
        k=3,
    )

    assert metrics == {
        "precision_at_k": 66.7,
        "recall_at_k": 100.0,
        "mrr": 100.0,
        "ndcg": 100.0,
    }


def test_runtime_retrieval_tool_executes_hybrid_pipeline():
    semantic = _result(
        "semantic",
        "semantic-1",
        0.01,
        "General performance discussion.",
    )
    lexical = _result(
        "tesla-q2",
        "tesla-revenue",
        0.20,
        "Tesla revenue growth accelerated.",
    )
    store = _HybridStore(
        vectors={7: [semantic, lexical]},
        corpora={7: [semantic, lexical]},
    )

    evidence = TenantRetrievalToolExecutor(
        HybridRetriever(_EmbeddingModel())
    ).execute(
        store=store,
        query="Tesla revenue growth",
        tenant_id=7,
        top_k=2,
    )

    assert evidence[0].metadata["retrieval_strategy"] == "hybrid_rrf"
    assert evidence[0].metadata["bm25_rank"] == 1
    assert store.lexical_calls == [7]


def test_chroma_lexical_corpus_is_tenant_scoped(tmp_path):
    store = ChromaEmbeddingStore(persist_directory=tmp_path / "chroma")
    store.add_documents(
        [
            VectorDocument(
                document_id="tenant-7",
                chunk_id="tenant-7-1",
                company="Tesla",
                content="Tenant seven revenue evidence.",
                embedding=[0.1, 0.2],
                metadata={
                    "collection": "financial_reports",
                    "tenant_id": 7,
                },
            ),
            VectorDocument(
                document_id="tenant-99",
                chunk_id="tenant-99-1",
                company="Tesla",
                content="Tenant ninety-nine revenue evidence.",
                embedding=[0.2, 0.1],
                metadata={
                    "collection": "financial_reports",
                    "tenant_id": 99,
                },
            ),
        ]
    )

    results = store.lexical_corpus(tenant_id=7)

    assert [result.chunk_id for result in results] == ["tenant-7-1"]
    assert results[0].metadata["tenant_id"] == 7
