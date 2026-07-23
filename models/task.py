import json
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant
    from models.user import User


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TaskType(str, Enum):
    PROCESS_DOCUMENT = "process_document"
    REFRESH_KNOWLEDGE = "refresh_knowledge"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskStatus.PENDING.value, index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    _payload: Mapped[str] = mapped_column("payload", Text, default="{}", nullable=False)
    _result: Mapped[str] = mapped_column("result", Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tasks")
    user: Mapped["User"] = relationship("User", back_populates="tasks")

    @property
    def payload(self) -> Dict[str, Any]:
        try:
            return json.loads(self._payload)
        except (json.JSONDecodeError, TypeError):
            return {}

    @payload.setter
    def payload(self, value: Dict[str, Any]) -> None:
        self._payload = json.dumps(value, ensure_ascii=False)

    @property
    def result(self) -> Dict[str, Any]:
        try:
            return json.loads(self._result)
        except (json.JSONDecodeError, TypeError):
            return {}

    @result.setter
    def result(self, value: Dict[str, Any]) -> None:
        self._result = json.dumps(value, ensure_ascii=False)
