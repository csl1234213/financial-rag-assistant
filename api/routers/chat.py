from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas.request import ChatRequest
from api.schemas.response import ChatResponse
from api.services.chat_service import ChatService
from auth.dependencies import get_optional_user
from core.usage_events import ResourceType, UsageEvent
from models.user import User
from services.plan_service import can_chat
from services.usage_service import record_usage
from storage.database import get_db

router = APIRouter(tags=["Chat"])

chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if current_user is not None and not can_chat(db, current_user.tenant_id):
        raise HTTPException(status_code=429, detail="Chat limit exceeded. Upgrade your plan.")

    response = chat_service.chat(
        question=request.question,
        company=request.company,
        tenant_id=current_user.tenant_id if current_user is not None else None,
        user_id=current_user.id if current_user is not None else None,
        thread_id=request.thread_id,
    )

    if current_user is not None:
        record_usage(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            event_type=UsageEvent.CHAT_REQUEST,
            resource_type=ResourceType.CHAT,
            quantity=1,
            metadata={"endpoint": "/api/v1/chat"},
            db=db,
        )

    return response
