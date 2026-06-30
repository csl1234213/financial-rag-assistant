import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from agent.agent_runtime import AgentRuntime
from agent.execution_engine import ExecutionEngine
from agent.execution_plan import StepType
from agent.query_planner import QueryPlanner
from agent.reasoning_engine import ReasoningEngine
from config import DEBUG_MODE
from core.citation_formatter import format_citations
from core.intent_analyzer import IntentAnalyzer
from core.report_builder import build_research_report
from core.research_analyzer import analyze_evidence
from document_loader import (
    load_documents,
)
from embedding import (
    load_embedding_model,
)
from llm.provider import call_llm
from llm.router import (
    CapabilityRoutingPolicy,
    ModelRouter,
    RoutingPolicy,
)
from prompt_builder import build_compare_prompt, build_prompt
from research_mode import (
    detect_research_mode,
)
from retrieval.hybrid_retriever import (
    HybridRetriever,
)
from retrieval.retrieval_context import RetrievalContext
from storage.vector_models import VectorDocument

# =========================
# Pipeline Composition
# =========================

PDF_FOLDER = "pdfs/"

_store = None
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = load_embedding_model()
    return _model


def _get_store():
    global _store
    if _store is None:
        from storage.chroma_store import ChromaEmbeddingStore
        _store = ChromaEmbeddingStore()
    return _store


# =========================
# Knowledge Base
# =========================

def refresh_knowledge_base():
    store = _get_store()
    model = _get_model()

    chunks = load_documents(PDF_FOLDER)

    for col_name in store.list_collections():
        store.delete_collection(col_name)

    store.create_collection("financial_reports")

    docs = []
    for chunk in chunks:
        embedding = model.encode(chunk["text"], convert_to_tensor=False).tolist()
        docs.append(VectorDocument(
            document_id=chunk["document_id"],
            chunk_id="%s_%d" % (chunk["document_id"], chunk["chunk_id"]),
            company=chunk["company"],
            content=chunk["text"],
            embedding=embedding,
            metadata={
                "source": chunk["source"],
                "quarter": chunk.get("quarter", ""),
                "collection": "financial_reports",
            }
        ))

    store.add_documents(docs)

    print(f"[RAG] Loaded {len(chunks)} chunks into ChromaDB")

    if len(chunks) > 0:
        print(chunks[0]["source"], chunks[0]["chunk_id"])


def get_chunk_count():
    store = _get_store()
    return store.count()


# =========================
# Runtime Wiring
# =========================

retriever = HybridRetriever(_get_model())
intent_analyzer = IntentAnalyzer()
query_planner = QueryPlanner()

engine = ExecutionEngine()
reasoning_engine = ReasoningEngine()


def _retrieve_handler(step, shared_context):
    store = _get_store()

    context = RetrievalContext(
        question=step.query or "",
        company=step.company,
        document_ids=step.document_ids or None,
        top_k=step.parameters.get("top_k", 4),
    )

    evidences = retriever.retrieve_evidence(
        context=context,
        store=store,
    )

    shared_context.setdefault("_all_evidence", []).extend(evidences)
    return evidences


engine.register_handler(StepType.RETRIEVE, _retrieve_handler)
engine.register_handler(StepType.COMPARE, lambda s, c: None)
engine.register_handler(StepType.SYNTHESIS, lambda s, c: None)

router = ModelRouter(
    policy=RoutingPolicy(CapabilityRoutingPolicy())
)

runtime = AgentRuntime(
    planner=query_planner,
    executor=engine,
    reasoner=reasoning_engine,
    retriever=retriever,
    intent_analyzer=intent_analyzer,
    router=router,
)


# =========================
# RAG MAIN
# =========================

def run_rag(question: str, company=None):

    research_mode = detect_research_mode(question)

    result = runtime.run(question, company)

    if research_mode == "compare":
        prompt = build_compare_prompt(question, result.context)
    else:
        prompt = build_prompt(question, result.context)

    if DEBUG_MODE:
        return (
            prompt,
            result.citations,
            result.context,
            research_mode,
            result.intent_result,
            result.evidence,
            result.plan,
            result.routing,
            result.planning,
        )

    if len(result.citations) == 0:
        return (
            "No relevant evidence found in uploaded documents.",
            [],
            "",
            research_mode,
            result.intent_result,
            result.evidence,
            result.plan,
            result.routing,
            result.planning,
        )

    answer = call_llm(prompt)

    evidence_stats = analyze_evidence(result.citations)

    report = build_research_report(
        question,
        answer,
        result.citations,
        evidence_stats,
        result.reasoning_result
    )

    citation_text = format_citations(result.citations)

    answer = answer + "\n\n" + citation_text

    return (
        report,
        result.citations,
        result.context,
        research_mode,
        result.intent_result,
        result.evidence,
        result.plan,
        result.routing,
        result.planning,
    )