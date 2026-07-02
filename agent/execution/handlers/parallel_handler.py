# ============================================================
# ParallelHandler — Execute multiple retrieval queries in parallel (placeholder)
# ============================================================
# Used when ExecutionResult.strategy == ExecutionStrategyType.PARALLEL
# Placeholder: delegates to RAG handler for now.
# Future: parallel execution of multiple retrieval sub-queries.
# ============================================================

import logging

from agent.execution.strategy_enums import ExecutionStrategyType
from agent.execution.execution_handler import (
    BaseExecutionHandler,
    ExecutionHandlerContext,
    ExecutionOutput,
)
from agent.execution.handlers.rag_handler import RagHandler

logger = logging.getLogger(__name__)


class ParallelHandler(BaseExecutionHandler):

    @property
    def strategy_type(self) -> ExecutionStrategyType:
        return ExecutionStrategyType.PARALLEL

    def execute(
        self,
        ctx: ExecutionHandlerContext,
    ) -> ExecutionOutput:
        logger.info("ParallelHandler: delegating to RAG (placeholder)")
        return RagHandler().execute(ctx)