# core_engine.py
from document_loader import load_documents, show_chunk_preview
from embedding import (
    load_embedding_model,
    get_embeddings,
    embed_chunks
)
from retrieval.hybrid_retriever import (
    retrieve_evidence,
    retrieve_multi_document,
    extract_local_context
)
from research_mode import (
    detect_research_mode,
    show_document_detection,
    expand_research_sources,
    filter_chunks_by_source
)
from prompt_builder import (
    build_prompt,
    build_compare_prompt
)
from llm.provider import call_llm
from config import DEBUG_MODE
from core.citation_formatter import (
    format_citations
)



# =========================
# 初始化（避免重复加载）
# =========================
PDF_FOLDER = "pdfs/"

chunks = None
model = None

def get_model():

    global model

    if model is None:

        model = load_embedding_model()

    return model


def init_engine():

    global chunks

    if chunks is not None:
        return

    chunks = load_documents(PDF_FOLDER)

    if DEBUG_MODE:
        show_chunk_preview(chunks)

model = get_model()
# =========================
# 主RAG流程
# =========================
def run_rag(question: str):
    """
    V1.6核心入口
    """

    global chunks, model

    init_engine()

    # -------------------------
    # 1. research mode
    # -------------------------
    research_mode = detect_research_mode(question)

    matched_sources = show_document_detection(question)
    matched_sources = expand_research_sources(
        matched_sources,
        research_mode
    )

    filtered_chunks = filter_chunks_by_source(
        chunks,
        matched_sources
    )

    if len(matched_sources) == 0:
        doc_name = "all"

    else:
        doc_name = "_".join(
            sorted(matched_sources)
        )

    filtered_embeddings = get_embeddings(
        model,
        filtered_chunks,
        doc_name
    )

    # -------------------------
    # 2. retrieval
    # -------------------------
    if len(matched_sources) > 1:

        multi_results = retrieve_multi_document(
            matched_sources,
            filtered_chunks,
            model,
            question
        )

        selected_chunks = []
        score_values = []
        top_k = []

        for item in multi_results:
            selected_chunks.append(item["chunk"])
            score_values.append(item["score"])
            top_k.append(len(selected_chunks) - 1)

        import torch
        scores = torch.tensor(score_values)

        context, citations = build_context(
            selected_chunks,
            top_k,
            scores,
            question
        )

    else:
        top_k, scores = retrieve_evidence(
            model,
            filtered_embeddings,
            question
        )

        context, citations = build_context(
            filtered_chunks,
            top_k,
            scores,
            question
        )
        if DEBUG_MODE:
            print()
            print("=" * 60)
            print("EVIDENCE CONTEXT")
            print("=" * 60)

            print(
                context[:1500]
            )
    # -------------------------
    # 3. prompt building
    # -------------------------
    if research_mode == "compare":
        prompt = build_compare_prompt(question, context)
    elif research_mode == "leader":
        prompt = build_compare_prompt(question, context)
    else:
        prompt = build_prompt(question, context)

    # -------------------------
    # 4. LLM call
    # -------------------------
    if DEBUG_MODE:
        return prompt, citations, context, research_mode

    answer = call_llm(prompt)

    citation_text = format_citations(
        citations
    )

    answer = (
            answer
            + "\n\n"
            + citation_text
    )

    return answer, citations, context, research_mode


# =========================
# 工具函数：构建context
# =========================
def build_context(chunks, top_k, scores, question):

    context = ""

    citations = []

    for rank, idx in enumerate(top_k):

        score = scores[idx].item()

        local_context = extract_local_context(
            chunks[idx]["text"],
            question
        )

        citations.append({
            "rank": rank + 1,
            "source": chunks[idx]["source"],
            "chunk_id": chunks[idx]["chunk_id"],
            "similarity": round(score, 4),
            "preview": local_context[:150]
        })

        context += f"""
[Evidence {rank + 1}]
Source: {chunks[idx]["source"]}
Chunk: {chunks[idx]["chunk_id"]}

{local_context}

"""

    return context, citations