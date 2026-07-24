import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.agent_runtime.factory import get_agent_graph, is_agent_available
from services.agent_runtime.schemas import AgentChatResponse

logger = logging.getLogger(__name__)


def _get_memory_path(tenant_id: int) -> str:
    memory_dir = Path(os.environ.get("AGENT_MEMORY_DIR", "storage/memory"))
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

    if tenant_id is not None:
        _set_tenant_memory_path(tenant_id)

    if is_agent_available():
        try:
            agent = get_agent_graph()
            result = agent["run_agent"](question, thread_id=thread_id)

            duration = round(time.time() - t0, 3)
            return {
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
        except Exception as e:
            logger.error(f"LangGraph agent error: {e}", exc_info=True)
            return _fallback_response(question, thread_id, str(e))

    return _fallback_response(question, thread_id)


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