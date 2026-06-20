# core/rag_engine.py
from document_loader import load_documents, show_chunk_preview
from embedding import (
    load_embedding_model,
    get_embeddings,
    embed_chunks
)
from retriever import (
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
from llm_client import generate_answer
from config import DEBUG_MODE


# =========================
# 初始化（避免重复加载）
# =========================
PDF_FOLDER = "pdfs/"

chunks = None
model = None


def init_engine():
    """
    只初始化一次模型和文档
    """

    global chunks, model

    if chunks is not None:
        return

    chunks = load_documents(PDF_FOLDER)
    show_chunk_preview(chunks)

    model = load_embedding_model()

    # 预热 Cache
    get_embeddings(
        model,
        chunks,
        PDF_FOLDER
    )
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

    answer = generate_answer(prompt)

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

        context += "=" * 60 + "\n"
        context += f"Evidence {rank + 1}\n"
        context += f"Source: {chunks[idx]['source']}\n"
        context += f"Chunk ID: {chunks[idx]['chunk_id']}\n"
        context += f"Similarity Score: {score:.4f}\n"
        context += "=" * 60 + "\n"

        context += local_context
        context += "\n\n"

    return context, citations