from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    thread_id: Optional[str] = "default"


class AgentChatResponse(BaseModel):
    answer: str
    thread_id: str
    tools_used: List[str] = []
    sources: List[Dict[str, Any]] = []
    companies: List[str] = []
    research_plan: List[Dict[str, Any]] = []
    quality_score: float = 0.0
    critique: Dict[str, Any] = {}
    revision_count: int = 0
    history: List[Dict[str, Any]] = []