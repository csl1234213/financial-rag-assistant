import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from document_loader import (
    load_documents,
    show_chunk_preview
)

from embedding import (
    load_embedding_model,
    get_embeddings
)

from retrieval.hybrid_retriever import (
    retrieve_evidence,
    extract_local_context,
)

from research_mode import (
    detect_research_mode,
)

from prompt_builder import (
    build_prompt,
    build_compare_prompt
)

from llm.provider import call_llm

from config import DEBUG_MODE
from core.citation_formatter import format_citations
from core.research_analyzer import analyze_evidence
from core.report_builder import build_research_report
from core.intent_analyzer import IntentAnalyzer
from agent.query_planner import QueryPlanner
from agent.execution_engine import ExecutionEngine
from agent.reasoning_engine import ReasoningEngine
from agent.execution_plan import StepType
from agent.agent_runtime import AgentRuntime
from retrieval.hybrid_retriever import HybridRetriever


# =========================
# Global State
# =========================

PDF_FOLDER = "pdfs/"
chunks = None
model = None
embeddings = None


# =========================
# Model init
# =========================

def get_model():
    global model
    if model is None:
        model = load_embedding_model()
    return model


# =========================
# Knowledge Base
# =========================

def init_engine(force_reload=False):
    global chunks, embeddings

    if chunks is not None and not force_reload:
        return

    chunks = load_documents(PDF_FOLDER)
    embeddings = get_embeddings(model, chunks, "global")

    if DEBUG_MODE:
        show_chunk_preview(chunks)


def refresh_knowledge_base():
    global chunks, embeddings

    chunks = load_documents(PDF_FOLDER)
    embeddings = get_embeddings(model, chunks, "global")

    print(f"[RAG] Loaded {len(chunks)} chunks")

    if len(chunks) > 0:
        print(chunks[0]["source"], chunks[0]["chunk_id"])


model = get_model()
retriever = HybridRetriever(model)
intent_analyzer = IntentAnalyzer()
query_planner = QueryPlanner()

engine = ExecutionEngine()
reasoning_engine = ReasoningEngine()


def _retrieve_handler(step, shared_context):
    global chunks, embeddings, retriever
    evidences = retriever.retrieve_evidence(
        chunks=chunks,
        embeddings=embeddings,
        question=step.query or "",
        company=step.company,
        document_ids=step.document_ids or None,
        top_k=step.parameters.get("top_k", 4),
    )
    shared_context.setdefault("_all_evidence", []).extend(evidences)
    return evidences


engine.register_handler(StepType.RETRIEVE, _retrieve_handler)
engine.register_handler(StepType.COMPARE, lambda s, c: None)
engine.register_handler(StepType.SYNTHESIS, lambda s, c: None)

runtime = AgentRuntime(
    planner=query_planner,
    executor=engine,
    reasoner=reasoning_engine,
    retriever=retriever,
    intent_analyzer=intent_analyzer,
)


# =========================
# RAG MAIN
# =========================

def run_rag(question: str, company=None):

    global chunks, model, embeddings

    init_engine()

    # -------------------------
    # 1. Router
    # -------------------------
    research_mode = detect_research_mode(question)

    # -------------------------
    # 2. Agent Runtime
    # -------------------------
    result = runtime.run(question, company)

    # -------------------------
    # 3. Prompt
    # -------------------------
    if research_mode == "compare":
        prompt = build_compare_prompt(question, result.context)
    else:
        prompt = build_prompt(question, result.context)

    # -------------------------
    # 4. LLM
    # -------------------------
    if DEBUG_MODE:
        return (
            prompt,
            result.citations,
            result.context,
            research_mode,
            result.intent_result,
            result.evidence,
            result.plan
        )

    if len(result.citations) == 0:
        return (
            "No relevant evidence found in uploaded documents.",
            [],
            "",
            research_mode,
            result.intent_result,
            result.evidence,
            result.plan
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
        result.plan
    )

def get_chunk_count():
    """
    返回当前知识库 Chunk 数量
    """

    global chunks

    if chunks is None:
        return 0

    return len(chunks)