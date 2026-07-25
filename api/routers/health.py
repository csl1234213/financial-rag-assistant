import logging
import os

from fastapi import APIRouter

from agent.__version__ import __version__
from core.knowledge_manager import get_document_count

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


def _check_database() -> str:
    try:
        from storage.database import SessionLocal

        db = SessionLocal()
        try:
            db.execute(1)
            return "ok"
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return "unavailable"


def _check_redis() -> str:
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        r.close()
        return "ok"
    except Exception:
        return "disabled"


@router.get("/health")
def health():
    db_status = _check_database()
    redis_status = _check_redis()

    try:
        doc_count = get_document_count()
    except Exception:
        doc_count = 0

    overall = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall,
        "service": "Financial Research Copilot",
        "version": __version__,
        "api": "ok",
        "runtime": "ok",
        "database": db_status,
        "redis": redis_status,
        "embedding_model": "loaded",
        "documents": doc_count,
    }