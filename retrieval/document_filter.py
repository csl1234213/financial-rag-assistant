# retrieval/document_filter.py

# retrieval/document_filter.py

def filter_documents(
        matched_sources,
        chunks,
        embeddings=None
):
    if not matched_sources:
        return chunks, embeddings

    filtered_chunks = []
    filtered_indices = []

    for i, chunk in enumerate(chunks):

        source_name = chunk["source"].lower()

        if any(

            company.lower() in source_name

            for company in matched_sources

        ):

            filtered_chunks.append(chunk)

            filtered_indices.append(i)

    if embeddings is None:
        return filtered_chunks, None

    filtered_embeddings = embeddings[
        filtered_indices
    ]

    return (
        filtered_chunks,
        filtered_embeddings
    )