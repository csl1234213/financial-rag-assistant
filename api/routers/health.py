from fastapi import APIRouter

from agent.__version__ import __version__
from core.knowledge_manager import get_document_count

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    try:
        doc_count = get_document_count()
    except Exception:
        doc_count = 0

    return {
        "status": "ok",
        "service": "Financial Research Copilot",
        "version": __version__,
        "api": "ok",
        "runtime": "ok",
        "embedding_model": "loaded",
        "documents": doc_count,
    }
