import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from config.worker import (
    HEARTBEAT_INTERVAL,
    WORKER_CONCURRENCY,
    WORKER_ID,
    WORKER_POLL_TIMEOUT,
)
from models.task import TaskStatus
from tasks.broker import get_broker
from tasks.heartbeat import get_heartbeat
from tasks.knowledge_tasks import process_document_task
from tasks.models import TaskType as TaskTypeEnum
from tasks.repository import get_task_repository
from tasks.retry import get_retry_count, should_retry

logger = logging.getLogger(__name__)

_HANDLERS = {
    TaskTypeEnum.PROCESS_DOCUMENT: process_document_task,
}

STALE_RECOVERY_INTERVAL_SECONDS = 60


class TaskWorker:
    def __init__(self, worker_id: str = None):
        self._running = False
        self._threads: list = []
        self._worker_id = worker_id or WORKER_ID
        self._hostname = socket.gethostname()
        self._last_recovery = datetime.now(timezone.utc)
        self._executor: ThreadPoolExecutor = None
        self._heartbeat = get_heartbeat(self._worker_id, self._hostname)

    def start(self):
        if self._running:
            return
        self._running = True
        self._executor = ThreadPoolExecutor(max_workers=WORKER_CONCURRENCY, thread_name_prefix="worker")
        self._heartbeat.send()

        self._threads = []
        for i in range(WORKER_CONCURRENCY):
            t = threading.Thread(
                target=self._run_thread,
                name=f"worker-{self._worker_id}-{i}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)

        self._health_thread = threading.Thread(
            target=self._health_loop,
            name=f"worker-health-{self._worker_id}",
            daemon=True,
        )
        self._health_thread.start()

        logger.info(f"TaskWorker started: {self._worker_id} with {WORKER_CONCURRENCY} threads")

    def stop(self):
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
        for t in self._threads:
            t.join(timeout=10)
        logger.info(f"TaskWorker stopped: {self._worker_id}")

    def _health_loop(self):
        while self._running:
            self._heartbeat.send()
            time.sleep(HEARTBEAT_INTERVAL)

    def _run_thread(self):
        while self._running:
            try:
                self._recover_stale_if_needed()
                self._process_next_task()
            except Exception as e:
                logger.exception(f"Worker {self._worker_id} error: {e}")
                time.sleep(1)

    def _recover_stale_if_needed(self):
        now = datetime.now(timezone.utc)
        if (now - self._last_recovery).total_seconds() < STALE_RECOVERY_INTERVAL_SECONDS:
            return
        self._last_recovery = now
        repo = get_task_repository()
        try:
            recovered = repo.recover_stale_tasks()
            if recovered > 0:
                logger.info(f"Worker {self._worker_id} recovered {recovered} stale tasks")
        finally:
            repo._db.close()

    def _process_next_task(self):
        broker = get_broker()
        broker.set_consumer_name(self._worker_id)
        task_public_id = None

        if broker.enabled:
            message = broker.consume_task(timeout=WORKER_POLL_TIMEOUT)
            if message is not None:
                task_public_id = message.get("task_id")

        if task_public_id is None:
            repo = get_task_repository()
            try:
                task = repo.claim_task()
                if task is None:
                    time.sleep(1)
                    return
                task_public_id = task.public_id
            finally:
                repo._db.close()

        self._execute_task(task_public_id)

    def _execute_task(self, task_public_id: str):
        broker = get_broker()
        repo = get_task_repository()
        try:
            task = repo.get_task(task_public_id)
            if task is None:
                logger.warning(f"Task {task_public_id} not found in DB")
                return

            if task.status != TaskStatus.PENDING.value:
                return

            claimed = repo.claim_task()
            if claimed is None or claimed.public_id != task_public_id:
                logger.warning(f"Worker {self._worker_id} failed to claim task {task_public_id}")
                return

            task.worker_id = self._worker_id
            task.locked_at = datetime.now(timezone.utc)
            repo._db.commit()

            handler = _HANDLERS.get(TaskTypeEnum(task.task_type))
            if handler is None:
                repo.update_task(
                    task_public_id,
                    status=TaskStatus.FAILED,
                    error_message=f"No handler for task type: {task.task_type}",
                )
                return

            handler(task_public_id)

            task = repo.get_task(task_public_id)
            if task and task.status == TaskStatus.FAILED.value:
                retry_count = get_retry_count(task)
                if should_retry(retry_count):
                    task.retry_count = retry_count + 1
                    repo._db.commit()
                    logger.info(
                        f"Worker {self._worker_id} retrying task {task_public_id} "
                        f"(attempt {task.retry_count})"
                    )
                    repo.update_task(task_public_id, status=TaskStatus.PENDING)
                    broker.retry_task(
                        task_id=task_public_id,
                        tenant_id=task.tenant_id,
                        task_type=task.task_type,
                    )
        finally:
            repo._db.close()


_worker: TaskWorker = None


def get_worker() -> TaskWorker:
    global _worker
    if _worker is None:
        _worker = TaskWorker()
    return _worker


def start_worker():
    get_worker().start()


def stop_worker():
    global _worker
    if _worker:
        _worker.stop()
        _worker = None
