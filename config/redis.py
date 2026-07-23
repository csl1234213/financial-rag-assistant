import os

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)

TASK_QUEUE_NAME = "financial:tasks:queue"

REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "true").lower() in ("true", "1", "yes")

MAX_RETRY = int(os.environ.get("TASK_MAX_RETRY", "3"))

__all__ = [
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DB",
    "REDIS_PASSWORD",
    "REDIS_ENABLED",
    "TASK_QUEUE_NAME",
    "MAX_RETRY",
]