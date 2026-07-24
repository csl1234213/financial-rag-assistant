import json
import logging
from typing import Any, Dict, Optional

from cache.redis import get_redis_client, is_redis_available

logger = logging.getLogger(__name__)

SESSION_TTL = 86400
SESSION_PREFIX = "agent:session:"


class SessionCache:
    def __init__(self):
        self._redis = get_redis_client()

    def _key(self, thread_id: str) -> str:
        return f"{SESSION_PREFIX}{thread_id}"

    def get_session(self, thread_id: str) -> Optional[Dict[str, Any]]:
        if not is_redis_available():
            return None
        try:
            data = self._redis.get(self._key(thread_id))
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
        return None

    def save_session(self, thread_id: str, state: Dict[str, Any]) -> bool:
        if not is_redis_available():
            return False
        try:
            self._redis.setex(
                self._key(thread_id),
                SESSION_TTL,
                json.dumps(state, ensure_ascii=False, default=str),
            )
            return True
        except Exception as e:
            logger.warning(f"Redis save error: {e}")
            return False

    def delete_session(self, thread_id: str) -> bool:
        if not is_redis_available():
            return False
        try:
            self._redis.delete(self._key(thread_id))
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    def exists(self, thread_id: str) -> bool:
        if not is_redis_available():
            return False
        try:
            return bool(self._redis.exists(self._key(thread_id)))
        except Exception:
            return False


session_cache = SessionCache()