from document_loader import load_documents
from retrieval.bm25_retriever import (
    build_bm25,
    bm25_search
)

chunks = load_documents("pdfs")

bm25 = build_bm25(chunks)

results = bm25_search(
    bm25,
    "Cybercab",
    chunks,
    top_k=5
)

for r in results:

    print(
        r["source"],
        r["chunk_id"]
    )