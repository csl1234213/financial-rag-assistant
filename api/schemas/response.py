from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatResponse(BaseModel):
    report: str
    citations: List[Dict[str, Any]]
    reasoning: Dict[str, Any]
    plan: Dict[str, Any]
    execution_time: float
    routing: Optional[Dict[str, Any]] = None
    planning: Optional[Dict[str, Any]] = None