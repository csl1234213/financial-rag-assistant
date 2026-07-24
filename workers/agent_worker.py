"""
Agent Worker — entrypoint for async agent task execution.

Usage:
    python -m workers.agent_worker

Consumes agent tasks from the task queue (Redis + DB fallback),
executes run_agent(), and persists results.
"""

import logging
import signal
import sys
import time

from tasks.worker import TaskWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("agent_worker")


def main():
    worker = TaskWorker(worker_id="agent-worker")
    logger.info("Starting Agent Worker...")

    worker.start()

    running = True

    def shutdown(signum, frame):
        nonlocal running
        logger.info(f"Received signal {signum}, shutting down...")
        running = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while running:
        time.sleep(1)

    worker.stop()
    logger.info("Agent Worker stopped")


if __name__ == "__main__":
    main()