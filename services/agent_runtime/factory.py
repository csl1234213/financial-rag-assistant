import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LANGGRAPH_AGENT = None
_LANGGRAPH_PATH = None


def _resolve_langgraph_path() -> Optional[Path]:
    langgraph_dir = Path(__file__).resolve().parent.parent.parent / "financial-rag-langchain"
    if langgraph_dir.exists() and (langgraph_dir / "agent" / "graph.py").exists():
        return langgraph_dir
    langgraph_dir = os.environ.get("LANGGRAPH_AGENT_PATH", "")
    if langgraph_dir:
        p = Path(langgraph_dir)
        if p.exists():
            return p
    return None


def _ensure_langgraph_importable():
    global _LANGGRAPH_PATH
    if _LANGGRAPH_PATH is not None:
        return _LANGGRAPH_PATH

    path = _resolve_langgraph_path()
    if path is None:
        logger.warning("financial-rag-langchain not found. Agent runtime will use fallback mode.")
        _LANGGRAPH_PATH = False
        return False

    path_str = str(path.resolve())
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    _LANGGRAPH_PATH = path_str
    return path_str


def get_agent_graph():
    global _LANGGRAPH_AGENT

    if _LANGGRAPH_AGENT is not None:
        return _LANGGRAPH_AGENT

    langgraph_path = _ensure_langgraph_importable()
    if not langgraph_path:
        _LANGGRAPH_AGENT = False
        return False

    try:
        from agent.graph import build_agent_graph, run_agent

        _LANGGRAPH_AGENT = {"build_agent_graph": build_agent_graph, "run_agent": run_agent}
        return _LANGGRAPH_AGENT
    except ImportError as e:
        logger.error(f"Failed to import LangGraph agent: {e}")
        _LANGGRAPH_AGENT = False
        return False


def is_agent_available() -> bool:
    return get_agent_graph() is not False