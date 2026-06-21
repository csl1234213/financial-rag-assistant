# retrieval/hybrid_retriever.py

"""
V1.9 Placeholder

Future:
- BM25
- Vector Search
- Hybrid Search
"""

from sentence_transformers import util
import re
from embedding import embed_chunks
from retrieval.bm25_retriever import (build_bm25, bm25_search)
from retrieval.document_filter import (
    filter_documents
)

def retrieve_vector_chunks(
        model,
        embeddings,
        question,
        chunks,
        top_k=5
):

    question_embedding = model.encode(
        question,
        convert_to_tensor=True
    )

    scores = util.cos_sim(
        question_embedding,
        embeddings
    )[0]

    top_indices = scores.argsort(
        descending=True
    )[:top_k]

    results = []

    for idx in top_indices:

        results.append(
            chunks[idx]
        )

    return results

def retrieve_evidence(model, embeddings, question):
    question_embedding = model.encode(question, convert_to_tensor=True)
    scores = util.cos_sim(question_embedding, embeddings)[0]
    top_k = scores.argsort(descending=True)[:4]
    return top_k, scores

def retrieve_company_chunks(
        company,
        chunks,
        embeddings,
        question,
        model,
        top_n=2
):
    company_chunks = []

    company_indices = []

    for i, chunk in enumerate(chunks):

        if company.lower() in chunk["source"].lower():
            company_chunks.append(chunk)

            company_indices.append(i)

    if len(company_chunks) == 0:
        return []

    company_embeddings = embeddings[company_indices]

    question_embedding = model.encode(

        question,

        convert_to_tensor=True

    )

    scores = util.cos_sim(

        question_embedding,

        company_embeddings

    )[0]

    top_indices = scores.argsort(

        descending=True

    )[:top_n]

    results = []

    for idx in top_indices:
        real_index = company_indices[idx]

        results.append({

            "chunk": chunks[real_index],

            "score": scores[idx].item()

        })

    return results

def retrieve_multi_document(

        matched_sources,

        chunks,

        model,

        question

):

    embeddings = embed_chunks(

        model,

        chunks

    )

    all_results = []

    for company in matched_sources:

        company_results = retrieve_company_chunks(

            company,

            chunks,

            embeddings,

            question,

            model,

            top_n=2

        )

        all_results.extend(

            company_results

        )

    all_results.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    return all_results

def extract_local_context(
        chunk,
        query,
        window=2
):

    keyword = extract_keyword(query)

    sentences = re.split(
        r'(?<=[.!?])\s+',
        chunk
    )

    hit_index = -1

    for i, sentence in enumerate(sentences):

        if keyword in sentence.lower():

            hit_index = i

            break

    if hit_index == -1:

        return chunk

    start = max(
        0,
        hit_index - window
    )

    end = min(
        len(sentences),
        hit_index + window + 1
    )

    local_context = " ".join(
        sentences[start:end]
    )

    return local_context

def extract_keyword(query):
    words = re.findall(

        r'\w+',

        query.lower()

    )

    words = [

        w for w in words

        if len(w) > 3

    ]

    if not words:
        return query.lower()

    return max(

        words,

        key=len

    )

def hybrid_search(
        query,
        chunks,
        embeddings,
        model,
        matched_sources=None,
        top_k=5
):
    chunks, embeddings = filter_documents(

        matched_sources,

        chunks,

        embeddings

    )

    print()
    print("=" * 60)
    print("DOCUMENT FILTER")
    print("=" * 60)

    print(
        f"Matched Sources: {matched_sources}"
    )

    print(
        f"Filtered Chunks: {len(chunks)}"
    )

    # Vector Search
    vector_results = retrieve_vector_chunks(

        model,

        embeddings,

        query,

        chunks,

        top_k

    )

    # BM25 Search
    bm25 = build_bm25(

        chunks

    )

    bm25_results = bm25_search(

        bm25,

        query,

        chunks,

        top_k

    )
    print()
    print("=" * 60)
    print("HYBRID SEARCH")
    print("=" * 60)

    print(
        f"Vector Results: {len(vector_results)}"
    )

    print(
        f"BM25 Results: {len(bm25_results)}"
    )

    # Merge
    # Score Fusion
    scores = {}

    for chunk in vector_results:
        key = (
            chunk["source"],
            chunk["chunk_id"]
        )

        scores[key] = scores.get(
            key,
            0
        ) + 1

    for chunk in bm25_results:
        key = (
            chunk["source"],
            chunk["chunk_id"]
        )

        scores[key] = scores.get(
            key,
            0
        ) + 1

    # Chunk Mapping
    chunk_map = {}

    for chunk in (

            vector_results +

            bm25_results

    ):
        key = (
            chunk["source"],
            chunk["chunk_id"]
        )

        chunk_map[key] = chunk

    # Ranking
    ranked = sorted(

        scores.items(),

        key=lambda x: x[1],

        reverse=True

    )
    print()

    for key, score in ranked:
        print(
            f"{key} -> {score}"
        )

    # Final Results
    results = []

    for key, score in ranked[:top_k]:
        results.append(

            chunk_map[key]

        )

    return results
