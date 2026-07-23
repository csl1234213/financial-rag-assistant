import logging
from datetime import datetime, timezone

from models.worker_node import WorkerNode
from storage.database import SessionLocal

logger = logging.getLogger(__name__)


class WorkerHeartbeat:
    def __init__(self, worker_id: str, hostname: str):
        self._worker_id = worker_id
        self._hostname = hostname
        self._db = None

    def send(self) -> bool:
        if self._db is not None:
            return self._send_with_db(self._db)

        db = SessionLocal()
        try:
            return self._send_with_db(db)
        finally:
            db.close()

    def _send_with_db(self, db) -> bool:
        try:
            node = db.query(WorkerNode).filter(
                WorkerNode.worker_id == self._worker_id
            ).first()

            if node is None:
                node = WorkerNode(
                    worker_id=self._worker_id,
                    hostname=self._hostname,
                    status="online",
                )
                db.add(node)
                db.commit()
                db.refresh(node)
                logger.info(f"Registered worker node: {self._worker_id}")

            node.last_seen = datetime.now(timezone.utc)
            node.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Heartbeat failed for {self._worker_id}: {e}")
            db.rollback()
            return False


def get_heartbeat(worker_id: str, hostname: str) -> WorkerHeartbeat:
    return WorkerHeartbeat(worker_id, hostname)