from fastapi import APIRouter

from core.core_engine import get_chunk_count
from core.knowledge_manager import (
    get_company_list,
    get_document_count,
    get_documents,
)

router = APIRouter(tags=["Knowledge"])


@router.get("/knowledge")
def knowledge_overview():
    return {
        "documents": get_documents(),
        "document_count": get_document_count(),
        "companies": get_company_list(),
    }


@router.get("/knowledge/statistics")
def knowledge_statistics():
    return {
        "documents": get_document_count(),
        "companies": len(get_company_list()),
        "chunks": get_chunk_count(),
        "embeddings": get_chunk_count(),
    }
