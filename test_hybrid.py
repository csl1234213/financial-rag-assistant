from document_loader import load_documents
from embedding import (
    load_embedding_model,
    get_embeddings
)

from retrieval.hybrid_retriever import (
    hybrid_search
)
import os
import pickle





# =========================
# INIT ONLY ONCE
# =========================
PDF_FOLDER = "pdfs"
CACHE_FILE = "cache/test_runtime.pkl"

if os.path.exists(CACHE_FILE):

    print("Loading cache...")

    with open(CACHE_FILE, "rb") as f:
        data = pickle.load(f)

    chunks = data["chunks"]
    embeddings = data["embeddings"]
    model = data["model"]

else:

    print("Building cache...")

    chunks = load_documents(PDF_FOLDER)

    model = load_embedding_model()

    embeddings = get_embeddings(
        model,
        chunks,
        PDF_FOLDER
    )

    os.makedirs("cache", exist_ok=True)

    with open(CACHE_FILE, "wb") as f:
        pickle.dump({
            "chunks": chunks,
            "embeddings": embeddings
        }, f)


# =========================
# 2. 测试集合
# =========================
from research_mode import show_document_detection
queries = [
    "Cybercab",
    "Optimus",
    "Robotaxi",
    "iPhone",
    "iPad",
    "Blackwell",
    "CUDA"
]

# =========================
# 3. 循环测试
# =========================
for query in queries:

    print()
    print("=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    # ❗ 关键：先做文档识别
    matched_sources = show_document_detection(query)

    print()
    print(f"Matched Sources: {matched_sources}")

    results = hybrid_search(
        query,
        chunks,
        embeddings,
        model,
        matched_sources,   # ✅ 关键补丁
        top_k=5
    )

    for i, r in enumerate(results, 1):

        print()
        print(f"Result {i}")
        print(f"Source: {r['source']}")
        print(f"Chunk ID: {r['chunk_id']}")
        print(r["text"][:250])