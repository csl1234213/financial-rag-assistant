from sentence_transformers import util
import re
from embedding import embed_chunks

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
