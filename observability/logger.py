import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredLogger:
    def __init__(self, name: str = "agent"):
        self._logger = logging.getLogger(name)

    def _format(self, level: str, event: str, **kwargs) -> str:
        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **kwargs,
        }
        return json.dumps(record, ensure_ascii=False, default=str)

    def info(self, event: str, **kwargs):
        self._logger.info(self._format("INFO", event, **kwargs))

    def warning(self, event: str, **kwargs):
        self._logger.warning(self._format("WARNING", event, **kwargs))

    def error(self, event: str, **kwargs):
        self._logger.error(self._format("ERROR", event, **kwargs))

    def debug(self, event: str, **kwargs):
        self._logger.debug(self._format("DEBUG", event, **kwargs))


agent_logger = StructuredLogger("agent")


def log_agent_request(
    request_id: str,
    tenant_id: int,
    thread_id: str,
    question: str,
    **kwargs,
):
    agent_logger.info(
        "agent_request_started",
        request_id=request_id,
        tenant_id=tenant_id,
        thread_id=thread_id,
        question=question[:200],
        **kwargs,
    )


def log_agent_response(
    request_id: str,
    tenant_id: int,
    thread_id: str,
    duration_ms: float,
    quality_score: float,
    tools_used: list,
    error: Optional[str] = None,
    **kwargs,
):
    agent_logger.info(
        "agent_request_completed",
        request_id=request_id,
        tenant_id=tenant_id,
        thread_id=thread_id,
        duration_ms=round(duration_ms, 2),
        quality_score=quality_score,
        tools_used=tools_used,
        error=error,
        **kwargs,
    )