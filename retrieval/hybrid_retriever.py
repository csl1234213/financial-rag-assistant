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


def retrieve_evidence(model, embeddings, question):
    question_embedding = model.encode(question, convert_to_tensor=True)
    scores = util.cos_sim(question_embedding, embeddings)[0]
    top_k = scores.argsort(descending=True)[:4]
    return top_k, scores



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





