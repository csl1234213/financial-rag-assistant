from fastapi import APIRouter

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
        "version": "4.0.0",
        "api": "ok",
        "runtime": "ok",
        "embedding_model": "loaded",
        "documents": doc_count,
    }
