import json
import logging
import time
from typing import Any, Dict, Optional

from cache.session import session_cache
from observability.logger import log_agent_request, log_agent_response
from observability.tracer import finish_trace, node_span, start_trace
from services.agent_runtime.checkpointing import (
    agent_checkpointer,
    scoped_checkpoint_thread_id,
)
from services.agent_runtime.factory import get_agent_graph, is_agent_available
from storage.agent.repository import AgentRepository
from storage.database import SessionLocal

logger = logging.getLogger(__name__)


def run_agent(
    question: str,
    thread_id: str = "default",
    tenant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    company: Optional[str] = None,
) -> Dict[str, Any]:
    t0 = time.time()
    scope_tenant_id = tenant_id or 0
    history = (
        _load_history(tenant_id, user_id, thread_id)
        if tenant_id is not None
        else []
    )
    cache_key = _cache_key(question, history, company)

    trace = start_trace(
        thread_id=thread_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    log_agent_request(
        request_id=trace.request_id,
        tenant_id=tenant_id or 0,
        thread_id=thread_id,
        question=question,
    )

    result = _try_cache(scope_tenant_id, user_id, thread_id, cache_key)
    if result:
        result["trace_id"] = trace.request_id
        result["duration"] = round(time.time() - t0, 3)
        finish_trace(
            trace,
            status="cache_hit",
            metadata={
                "cache": True,
                "duration_ms": result["duration"] * 1000,
            },
        )
        return result

    if tenant_id is not None:
        _record_message(
            tenant_id,
            user_id,
            thread_id,
            role="user",
            content=question,
        )

    if is_agent_available():
        try:
            agent = get_agent_graph()
            with agent_checkpointer(tenant_id, user_id) as checkpointer:
                checkpoint_thread_id = (
                    scoped_checkpoint_thread_id(
                        scope_tenant_id,
                        user_id,
                        thread_id,
                    )
                    if checkpointer is not None
                    else None
                )
                with node_span(
                    trace,
                    "agent_graph",
                    metadata={
                        "thread_id": thread_id,
                        "durable": checkpointer is not None,
                    },
                ):
                    result = agent["run_agent"](
                        question,
                        company=company,
                        thread_id=thread_id,
                        tenant_id=scope_tenant_id,
                        user_id=user_id,
                        history=history,
                        trace=trace,
                        checkpointer=checkpointer,
                        checkpoint_thread_id=checkpoint_thread_id,
                    )

            duration = round(time.time() - t0, 3)
            output = {
                "answer": result.get("answer", ""),
                "thread_id": result.get("thread_id", thread_id),
                "tools_used": result.get("tools_used", []),
                "sources": result.get("sources", []),
                "citations": result.get("citations", []),
                "research_mode": result.get("research_mode", "default"),
                "evidence_count": result.get("evidence_count", 0),
                "plan": result.get("plan", {}),
                "companies": result.get("companies", []),
                "research_plan": result.get("research_plan", []),
                "quality_score": result.get("quality_score", 0.0),
                "critique": result.get("critique", {}),
                "revision_count": result.get("revision_count", 0),
                "intent": result.get("intent", {}),
                "routing": result.get("routing"),
                "planning": result.get("planning"),
                "execution": result.get("execution"),
                "workflow": result.get("workflow"),
                "history": [],
                "duration": duration,
                "trace_id": trace.request_id,
            }

            if tenant_id is not None:
                _record_message(
                    tenant_id,
                    user_id,
                    thread_id,
                    role="assistant",
                    content=output["answer"],
                    metadata={
                        "trace_id": trace.request_id,
                        "tools_used": output["tools_used"],
                        "quality_score": output["quality_score"],
                    },
                )
                output["history"] = _load_history(tenant_id, user_id, thread_id)

            _save_to_cache(
                scope_tenant_id,
                user_id,
                thread_id,
                cache_key,
                output,
            )

            finish_trace(
                trace,
                status="success",
                metadata={
                    "duration_ms": duration * 1000,
                    "quality_score": output["quality_score"],
                    "tools_used": output["tools_used"],
                    "revision_count": output["revision_count"],
                },
            )

            log_agent_response(
                request_id=trace.request_id,
                tenant_id=tenant_id or 0,
                thread_id=thread_id,
                duration_ms=duration * 1000,
                quality_score=output["quality_score"],
                tools_used=output["tools_used"],
            )
            return output

        except Exception as e:
            logger.error(f"LangGraph agent error: {e}", exc_info=True)
            duration = round(time.time() - t0, 3)
            finish_trace(
                trace,
                status="failed",
                metadata={
                    "error": str(e),
                    "duration_ms": duration * 1000,
                },
            )
            log_agent_response(
                request_id=trace.request_id,
                tenant_id=tenant_id or 0,
                thread_id=thread_id,
                duration_ms=duration * 1000,
                quality_score=0.0,
                tools_used=[],
                error=str(e),
            )
            return _fallback_response(question, thread_id, str(e), trace.request_id)
    duration = round(time.time() - t0, 3)
    finish_trace(
        trace,
        status="fallback",
        metadata={
            "duration_ms": duration * 1000,
            "reason": "agent_unavailable",
        },
    )
    return _fallback_response(question, thread_id, "", trace.request_id)


def _load_history(
    tenant_id: int,
    user_id: Optional[int],
    thread_id: str,
    limit: int = 8,
) -> list[Dict[str, Any]]:
    """Read a tenant- and user-scoped history for prompt construction."""
    db = SessionLocal()
    try:
        repo = AgentRepository(db)
        session = repo.get_session(tenant_id, user_id, thread_id)
        if session is None:
            return []
        messages = repo.get_messages(session.id, limit=limit)
        return [
            {
                "role": message.role,
                "content": message.content,
                "metadata": message.metadata_dict,
            }
            for message in messages
        ]
    except Exception as exc:
        logger.warning("Unable to load agent session history: %s", exc)
        return []
    finally:
        db.close()


def _record_message(
    tenant_id: int,
    user_id: Optional[int],
    thread_id: str,
    *,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist a conversation turn without making the chat request fail."""
    db = SessionLocal()
    try:
        repo = AgentRepository(db)
        session = repo.get_or_create_session(tenant_id, user_id, thread_id)
        repo.add_message(session.id, role, content, metadata)
        repo.touch_session(session)
    except Exception as exc:
        logger.warning("Unable to persist agent session message: %s", exc)
    finally:
        db.close()


def _cache_key(
    question: str,
    history: list[Dict[str, Any]],
    company: Optional[str],
) -> str:
    return json.dumps(
        {"question": question, "company": company, "history": history},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _try_cache(
    tenant_id: int,
    user_id: Optional[int],
    thread_id: str,
    request_key: str,
) -> Optional[Dict[str, Any]]:
    cached = session_cache.get_session(
        thread_id,
        tenant_id,
        request_key,
        user_id=user_id or 0,
    )
    if cached:
        logger.info("Cache hit for tenant=%s thread=%s", tenant_id, thread_id)
        return cached
    return None


def _save_to_cache(
    tenant_id: int,
    user_id: Optional[int],
    thread_id: str,
    request_key: str,
    result: Dict[str, Any],
):
    try:
        session_cache.save_session(
            thread_id,
            result,
            tenant_id,
            request_key,
            user_id=user_id or 0,
        )
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


def _fallback_response(question: str, thread_id: str, error: str = "", trace_id: str = "") -> Dict[str, Any]:
    # ``error`` is intentionally accepted for backwards compatibility but is
    # never reflected to clients. The full exception remains in structured
    # logs and the trace identified by ``trace_id``.
    del error
    return {
        "answer": f"[Agent Runtime Fallback] Unable to process: '{question}'. "
                  "Please retry or inspect the runtime trace.",
        "thread_id": thread_id,
        "tools_used": [],
        "sources": [],
        "citations": [],
        "research_mode": "default",
        "evidence_count": 0,
        "plan": {},
        "companies": [],
        "research_plan": [],
        "quality_score": 0.0,
        "critique": {},
        "revision_count": 0,
        "planning": None,
        "routing": None,
        "execution": None,
        "workflow": None,
        "history": [],
        "duration": 0,
        "trace_id": trace_id,
    }
