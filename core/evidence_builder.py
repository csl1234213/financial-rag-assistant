# core/evidence_builder.py


def build_evidence_context(results):

    context = ""

    for i, chunk in enumerate(results, start=1):

        source = chunk["source"]

        chunk_id = chunk["chunk_id"]

        text = chunk["text"]

        context += f"""
[Evidence {i}]
Source: {source}
Chunk: {chunk_id}

{text}

"""

    return context