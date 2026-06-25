import sys
from pathlib import Path
import os

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
    extract_local_context
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


# =========================
# Global State
# =========================

PDF_FOLDER = "pdfs/"
chunks = None
model = None


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
    global chunks

    if chunks is not None and not force_reload:
        return

    chunks = load_documents(PDF_FOLDER)

    if DEBUG_MODE:
        show_chunk_preview(chunks)


def refresh_knowledge_base():
    global chunks

    chunks = load_documents(PDF_FOLDER)

    print(f"[RAG] Loaded {len(chunks)} chunks")

    if len(chunks) > 0:
        print(chunks[0]["source"], chunks[0]["chunk_id"])


model = get_model()


# =========================
# RAG MAIN
# =========================

def run_rag(question: str):

    global chunks, model

    init_engine()

    # -------------------------
    # 1. Router
    # -------------------------
    research_mode = detect_research_mode(question)


    # -------------------------
    # 2. Embedding + Retrieval
    # -------------------------
    all_embeddings = get_embeddings(
        model,
        chunks,
        "global"
    )

    top_k, scores = retrieve_evidence(
        model,
        all_embeddings,
        question
    )

    # filter invalid indices
    valid_sources = set(matched_sources)

    top_k = [
        i for i in top_k
        if chunks[i]["source"] in valid_sources
    ]

    context, citations = build_context(
        chunks,
        top_k,
        scores,
        question
    )

    print("\n====================")
    print("CITATIONS")
    print(citations)

    print("====================")
    print("CONTEXT")
    print(context[:800])
    print("====================\n")

    # -------------------------
    # 3. Prompt
    # -------------------------
    if research_mode == "compare":
        prompt = build_compare_prompt(question, context)
    else:
        prompt = build_prompt(question, context)

    # -------------------------
    # 4. LLM
    # -------------------------
    if DEBUG_MODE:
        return prompt, citations, context, research_mode

    if len(citations) == 0:
        return (
            "No relevant evidence found in uploaded documents.",
            [],
            "",
            research_mode
        )

    answer = call_llm(prompt)

    evidence_stats = analyze_evidence(citations)

    report = build_research_report(
        question,
        answer,
        citations,
        evidence_stats
    )

    citation_text = format_citations(citations)

    answer = answer + "\n\n" + citation_text

    return (
        report,
        citations,
        context,
        research_mode
    )
