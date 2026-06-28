from fastapi import APIRouter

from api.schemas.request import ChatRequest
from api.schemas.response import ChatResponse
from api.services.chat_service import ChatService

router = APIRouter(tags=["Chat"])

chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return chat_service.chat(
        question=request.question,
        company=request.company,
    )
