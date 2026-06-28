from fastapi import APIRouter

from core.core_engine import refresh_knowledge_base

router = APIRouter(tags=["System"])


@router.post("/refresh")
def refresh():
    refresh_knowledge_base()

    return {
        "status": "ok",
        "message": "knowledge base refreshed",
    }
