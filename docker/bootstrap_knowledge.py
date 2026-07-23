"""
Idempotent demo knowledge bootstrap.
Detects existing ChromaDB data — skips init if already populated.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHROMA_DIR = os.environ.get("CHROMA_PATH", os.path.join(os.path.dirname(__file__), "..", "chroma_db"))


def _chroma_has_data() -> bool:
    try:
        from storage.chroma_store import ChromaEmbeddingStore
        store = ChromaEmbeddingStore(persist_directory=CHROMA_DIR)
        return store.count() > 0
    except Exception:
        return False


def bootstrap():
    if _chroma_has_data():
        print("[Bootstrap] Knowledge base already populated — skipping init.")
        return

    print("[Bootstrap] Knowledge base empty — initializing demo data...")
    from core.core_engine import refresh_knowledge_base
    refresh_knowledge_base()

    from storage.chroma_store import ChromaEmbeddingStore
    store = ChromaEmbeddingStore(persist_directory=CHROMA_DIR)
    print(f"[Bootstrap] Done — {store.count()} chunks indexed.")


if __name__ == "__main__":
    bootstrap()
