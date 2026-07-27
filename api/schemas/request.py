from typing import Optional

from pydantic import BaseModel, Field, field_validator

from api.schemas.thread import MAX_THREAD_ID_LENGTH, validate_thread_id


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    company: Optional[str] = None
    thread_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=MAX_THREAD_ID_LENGTH,
    )
    stream: bool = False

    _validate_thread_id = field_validator("thread_id")(validate_thread_id)
