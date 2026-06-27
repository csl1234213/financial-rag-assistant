# retrieval/hybrid_retriever.py

"""
V3 Hybrid Retriever

Supports:
- retrieve()       → RetrievalResult (legacy)
- retrieve_evidence() → List[Evidence] (V3 Agent pipeline)
"""

from sentence_transformers import util
import re
from dataclasses import dataclass
from typing import List
from embedding import get_embeddings
from agent.reasoning_models import Evidence



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

@dataclass
class RetrievalResult:
    """
    Unified retrieval result.

    Phase 2:
    Prepare for multi-document retrieval.
    """

    top_k: List

    scores: List

    chunks: List

    document_ids: List[str]

    companies: List[str]

class HybridRetriever:

    def __init__(self, model):

        self.model = model

    def retrieve(
            self,
            chunks,
            embeddings,
            question,
            company=None,
            document_ids=None,
            top_k=4,
    ):
        filtered_chunks = chunks
        if company:
            filtered_chunks = [
                c for c in filtered_chunks
                if c.get("company") == company
            ]
        if document_ids:
            filtered_chunks = [
                c for c in filtered_chunks
                if c.get("document_id") in document_ids
            ]

        indexes, scores = retrieve_evidence(
            self.model,
            embeddings,
            question
        )

        return RetrievalResult(
            top_k=indexes,
            scores=scores,
            chunks=chunks,
            document_ids=[
                filtered_chunks[i].get("document_id", "unknown")
                for i in indexes
                if i < len(filtered_chunks)
            ],
            companies=[company] if company else []
        )

    def retrieve_evidence(
            self,
            chunks,
            embeddings,
            question,
            company=None,
            document_ids=None,
            top_k=4,
    ) -> List[Evidence]:
        """
        V3: Retrieve and return structured Evidence objects.

        This is the primary interface for the Agent pipeline.
        """
        result = self.retrieve(
            chunks=chunks,
            embeddings=embeddings,
            question=question,
            company=company,
            document_ids=document_ids,
            top_k=top_k,
        )

        evidences = []

        for rank, idx in enumerate(result.top_k):
            if idx >= len(result.chunks):
                continue

            chunk = result.chunks[idx]
            score = result.scores[idx].item() if idx < len(result.scores) else 0.0

            local_context = extract_local_context(
                chunk["text"],
                question
            )

            evidences.append(Evidence(
                content=local_context,
                source=chunk.get("source", ""),
                company=company or chunk.get("company", ""),
                confidence=round(score, 4),
                metadata={
                    "rank": rank + 1,
                    "chunk_id": chunk.get("chunk_id", ""),
                    "document_id": chunk.get("document_id", "unknown"),
                }
            ))

        return evidences

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