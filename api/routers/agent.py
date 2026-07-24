import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from core.usage_events import ResourceType, UsageEvent
from models.user import User
from services.agent_runtime.runtime import run_agent
from services.plan_service import can_chat
from services.usage_service import record_usage
from storage.database import get_db

router = APIRouter(prefix="/agent", tags=["Agent Chat"])


class AgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    thread_id: Optional[str] = "default"


@router.post("/chat")
def agent_chat(
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id

    if not can_chat(db, tenant_id):
        raise HTTPException(
            status_code=429,
            detail="Agent chat limit exceeded. Upgrade your plan for more agent interactions.",
        )

    t0 = time.time()

    result = run_agent(
        question=request.question,
        thread_id=request.thread_id or "default",
        tenant_id=tenant_id,
        user_id=current_user.id,
    )

    duration = round(time.time() - t0, 3)

    record_usage(
        tenant_id=tenant_id,
        user_id=current_user.id,
        event_type=UsageEvent.CHAT_REQUEST,
        resource_type=ResourceType.CHAT,
        quantity=1,
        metadata={
            "endpoint": "/api/v1/agent/chat",
            "thread_id": request.thread_id,
            "tools_used": result.get("tools_used", []),
            "quality_score": result.get("quality_score", 0.0),
            "duration": duration,
            "agent_type": "langgraph",
        },
        db=db,
    )

    return {
        "answer": result["answer"],
        "thread_id": result["thread_id"],
        "tools_used": result["tools_used"],
        "sources": result["sources"],
        "companies": result["companies"],
        "research_plan": result["research_plan"],
        "quality_score": result["quality_score"],
        "critique": result["critique"],
        "revision_count": result["revision_count"],
        "history": result.get("history", []),
        "duration": duration,
    }