from typing import Any, Dict, List

from retrieval.hybrid_retriever import extract_local_context


def build_context(result, question):
    """
    Legacy: build context from RetrievalResult.
    """
    chunks = result.chunks
    scores = result.scores
    top_k_indices = result.top_k

    context = ""
    citations = []

    max_len = len(chunks)

    for rank, idx in enumerate(top_k_indices):

        if idx >= max_len:
            continue

        score = scores[idx].item() if idx < len(scores) else 0.0

        chunk = chunks[idx]

        local_context = extract_local_context(
            chunk["text"],
            question
        )

        citations.append({
            "rank": rank + 1,
            "source": chunk["source"],
            "chunk_id": chunk["chunk_id"],
            "similarity": round(score, 4),
            "preview": local_context[:150]
        })

        context += f"""
[Evidence {rank + 1}]
Source: {chunk["source"]}
Chunk: {chunk["chunk_id"]}

{local_context}

"""

    return context, citations


def build_context_from_evidence(evidences) -> tuple:
    """
    V3: Build context and citations from Evidence list.

    Agent Runtime calls this after execution.
    Belongs to core/ (presentation layer), not agent/ (orchestration layer).
    """
    context = ""
    citations: List[Dict[str, Any]] = []

    for i, ev in enumerate(evidences):
        citations.append({
            "rank": i + 1,
            "source": ev.source,
            "chunk_id": ev.metadata.get("chunk_id", ""),
            "similarity": ev.confidence,
            "preview": ev.content[:150],
        })
        context += f"""
[Evidence {i + 1}]
Source: {ev.source}
Chunk: {ev.metadata.get("chunk_id", "")}

{ev.content}

"""

    return context, citations
