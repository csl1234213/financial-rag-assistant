import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from cache.session import session_cache
from config.storage import storage_config
from services.agent_runtime.factory import get_agent_graph, is_agent_available
from storage.agent.checkpoint import PostgresSaver
from storage.agent.repository import AgentRepository
from storage.database import SessionLocal

logger = logging.getLogger(__name__)


def _get_memory_path(tenant_id: int) -> str:
    memory_dir = Path(storage_config.agent_memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)
    db_path = memory_dir / f"tenant_{tenant_id}.db"
    return str(db_path.resolve())


def _set_tenant_memory_path(tenant_id: int):
    db_path = _get_memory_path(tenant_id)
    os.environ["LANGGRAPH_CHECKPOINT_DB"] = db_path
    os.environ["LANGGRAPH_CHECKPOINT_DB_PATH"] = db_path
    return db_path


def run_agent(
    question: str,
    thread_id: str = "default",
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    t0 = time.time()

    result = _try_cache(thread_id)
    if result:
        result["duration"] = round(time.time() - t0, 3)
        return result

    if tenant_id is not None:
        _set_tenant_memory_path(tenant_id)
        _ensure_session(tenant_id, user_id, thread_id)

    if is_agent_available():
        try:
            checkpoint_saver = _create_checkpoint_saver(tenant_id)
            agent = get_agent_graph()
            result = agent["run_agent"](question, thread_id=thread_id)

            if checkpoint_saver:
                _save_checkpoint(checkpoint_saver, thread_id, result)

            duration = round(time.time() - t0, 3)
            output = {
                "answer": result.get("answer", ""),
                "thread_id": result.get("thread_id", thread_id),
                "tools_used": result.get("tools_used", []),
                "sources": result.get("sources", []),
                "companies": result.get("companies", []),
                "research_plan": result.get("research_plan", []),
                "quality_score": result.get("quality_score", 0.0),
                "critique": result.get("critique", {}),
                "revision_count": result.get("revision_count", 0),
                "history": [],
                "duration": duration,
            }

            _save_to_cache(thread_id, output)
            return output

        except Exception as e:
            logger.error(f"LangGraph agent error: {e}", exc_info=True)
            return _fallback_response(question, thread_id, str(e))

    return _fallback_response(question, thread_id)


def _ensure_session(tenant_id: int, user_id: Optional[int], thread_id: str):
    db = SessionLocal()
    try:
        repo = AgentRepository(db)
        repo.get_or_create_session(tenant_id, user_id, thread_id)
    finally:
        db.close()


def _create_checkpoint_saver(tenant_id: Optional[int]) -> Optional[PostgresSaver]:
    if storage_config.use_postgres and tenant_id is not None:
        db = SessionLocal()
        try:
            return PostgresSaver(db, tenant_id)
        except Exception as e:
            logger.warning(f"PostgresSaver unavailable: {e}")
    return None


def _save_checkpoint(saver: PostgresSaver, thread_id: str, result: Dict[str, Any]):
    try:
        saver.put(
            {"configurable": {"thread_id": thread_id}},
            {
                "answer": result.get("answer", ""),
                "tools_used": result.get("tools_used", []),
                "quality_score": result.get("quality_score", 0.0),
                "sources": result.get("sources", []),
            },
        )
    except Exception as e:
        logger.warning(f"Checkpoint save failed: {e}")


def _try_cache(thread_id: str) -> Optional[Dict[str, Any]]:
    cached = session_cache.get_session(thread_id)
    if cached:
        logger.info(f"Cache hit for thread: {thread_id}")
        return cached
    return None


def _save_to_cache(thread_id: str, result: Dict[str, Any]):
    try:
        session_cache.save_session(thread_id, result)
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


def _fallback_response(question: str, thread_id: str, error: str = "") -> Dict[str, Any]:
    return {
        "answer": f"[Agent Runtime Fallback] Unable to process: '{question}'. "
                  f"Please ensure financial-rag-langchain is installed and configured. "
                  f"{'Error: ' + error if error else ''}",
        "thread_id": thread_id,
        "tools_used": [],
        "sources": [],
        "companies": [],
        "research_plan": [],
        "quality_score": 0.0,
        "critique": {},
        "revision_count": 0,
        "history": [],
        "duration": 0,
    }