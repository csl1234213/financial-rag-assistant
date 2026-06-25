def build_context(chunks, top_k, scores, question):

    context = ""
    citations = []

    max_len = len(chunks)

    for rank, idx in enumerate(top_k):

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