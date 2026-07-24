import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from storage.agent.models import AgentCheckpoint, AgentMessage, AgentSession

logger = logging.getLogger(__name__)


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---- Session ----

    def create_session(self, tenant_id: int, user_id: Optional[int], thread_id: str) -> AgentSession:
        session = AgentSession(tenant_id=tenant_id, user_id=user_id, thread_id=thread_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, tenant_id: int, thread_id: str) -> Optional[AgentSession]:
        return (
            self.db.query(AgentSession)
            .filter(
                AgentSession.tenant_id == tenant_id,
                AgentSession.thread_id == thread_id,
            )
            .first()
        )

    def get_or_create_session(self, tenant_id: int, user_id: Optional[int], thread_id: str) -> AgentSession:
        session = self.get_session(tenant_id, thread_id)
        if session is None:
            session = self.create_session(tenant_id, user_id, thread_id)
        return session

    def touch_session(self, session: AgentSession):
        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    # ---- Message ----

    def add_message(self, session_id: int, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> AgentMessage:
        msg = AgentMessage(
            session_id=session_id,
            role=role,
            content=content,
            _metadata=json.dumps(metadata or {}, ensure_ascii=False, default=str),
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages(self, session_id: int, limit: int = 50) -> List[AgentMessage]:
        return (
            self.db.query(AgentMessage)
            .filter(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
            .all()
        )[::-1]

    # ---- Checkpoint ----

    def save_checkpoint(self, thread_id: str, checkpoint_data: Dict[str, Any]) -> AgentCheckpoint:
        cp = AgentCheckpoint(
            thread_id=thread_id,
            checkpoint_data=json.dumps(checkpoint_data, ensure_ascii=False, default=str),
        )
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)
        return cp

    def get_latest_checkpoint(self, thread_id: str) -> Optional[AgentCheckpoint]:
        return (
            self.db.query(AgentCheckpoint)
            .filter(AgentCheckpoint.thread_id == thread_id)
            .order_by(AgentCheckpoint.created_at.desc())
            .first()
        )

    def get_checkpoint(self, checkpoint_id: int) -> Optional[AgentCheckpoint]:
        return self.db.query(AgentCheckpoint).filter(AgentCheckpoint.id == checkpoint_id).first()

    def delete_checkpoints(self, thread_id: str) -> int:
        count = (
            self.db.query(AgentCheckpoint)
            .filter(AgentCheckpoint.thread_id == thread_id)
            .delete()
        )
        self.db.commit()
        return count