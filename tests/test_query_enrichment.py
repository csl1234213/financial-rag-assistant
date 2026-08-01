from retrieval.hybrid_retriever import HybridRetriever
from retrieval.query_enrichment import enrich_financial_query
from retrieval.retrieval_context import RetrievalContext
from storage.vector_models import SearchResult


class _Embedding(list):
    def tolist(self):
        return list(self)


class _CapturingModel:
    def __init__(self):
        self.inputs: list[str] = []

    def encode(
        self,
        text,
        convert_to_tensor=False,
        normalize_embeddings=False,
    ):
        del convert_to_tensor, normalize_embeddings
        self.inputs.append(text)
        return _Embedding([0.1, 0.2])


class _Store:
    def __init__(self, documents):
        self.documents = documents

    def similarity_search(self, *, query_embedding, top_k, tenant_id):
        del query_embedding, tenant_id
        return self.documents[:top_k]

    def lexical_corpus(self, tenant_id=None):
        del tenant_id
        return self.documents


def _result(chunk_id: str, content: str) -> SearchResult:
    return SearchResult(
        document_id="tesla-q2",
        chunk_id=chunk_id,
        score=0.2,
        content=content,
        metadata={
            "tenant_id": 7,
            "company": "Tesla",
            "source": "Tesla_Q2_2025.pdf",
        },
    )


def test_chinese_financial_query_adds_auditable_english_hints():
    enriched = enrich_financial_query(
        "特斯拉2025年第二季度汽车业务收入增长多少？",
        "Tesla",
    )

    assert enriched.startswith("特斯拉2025年第二季度")
    assert enriched.count("Tesla") == 1
    assert "Q2 second quarter" in enriched
    assert "automotive" in enriched
    assert "revenue" in enriched
    assert "growth" in enriched


def test_non_financial_english_query_is_not_rewritten():
    question = "What is AI?"

    assert enrich_financial_query(question) == question


def test_english_financial_query_adds_exact_table_terms():
    enriched = enrich_financial_query(
        "Analyze Tesla Q2 2025 automotive revenue growth.",
        "Tesla",
    )

    assert enriched.startswith(
        "Analyze Tesla Q2 2025 automotive revenue growth."
    )
    assert "Q2-2025" in enriched
    assert "Q2'25" in enriched
    assert "total automotive revenues" in enriched
    assert "quarterly total revenues" in enriched


def test_fiscal_quarter_adds_exact_filing_period_aliases():
    enriched = enrich_financial_query(
        "英伟达2027财年第一季度毛利率是多少？",
        "NVIDIA",
    )

    assert "Q1 FY27" in enriched
    assert "Q1 Fiscal 2027" in enriched
    assert "gross margin" in enriched


def test_hybrid_retrieval_uses_enriched_query_for_embedding_and_bm25():
    generic = _result("generic", "Tesla product and delivery overview.")
    financial = _result(
        "financial",
        "Q2 total automotive revenue increased year over year.",
    )
    model = _CapturingModel()

    results = HybridRetriever(model).retrieve(
        RetrievalContext(
            question="特斯拉第二季度汽车业务收入增长如何？",
            company="Tesla",
            tenant_id=7,
            top_k=2,
        ),
        _Store([generic, financial]),
    )

    assert model.inputs
    assert model.inputs[0].startswith("query: 特斯拉第二季度")
    assert "automotive" in model.inputs[0]
    assert "revenue" in model.inputs[0]
    assert results[0].chunk_id == "financial"
    assert results[0].metadata["bm25_rank"] == 1
    assert results[0].metadata["lexical_weight"] == 2.0
