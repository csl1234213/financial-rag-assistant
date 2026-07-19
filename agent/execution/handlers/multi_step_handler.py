# ============================================================
# MultiStepHandler — Execute multi-step reasoning workflow (placeholder)
# ============================================================
# Used when ExecutionResult.strategy == ExecutionStrategyType.MULTI_STEP
# Placeholder: delegates to RAG handler for now.
# Future: chain of reasoning steps (retrieve → analyze → synthesize).
# ============================================================

import logging

from agent.execution.execution_handler import (
    BaseExecutionHandler,
    ExecutionHandlerContext,
    ExecutionOutput,
)
from agent.execution.handlers.rag_handler import RagHandler
from agent.execution.strategy_enums import ExecutionStrategyType

logger = logging.getLogger(__name__)


class MultiStepHandler(BaseExecutionHandler):
    @property
    def strategy_type(self) -> ExecutionStrategyType:
        return ExecutionStrategyType.MULTI_STEP

    def execute(
        self,
        ctx: ExecutionHandlerContext,
    ) -> ExecutionOutput:
        logger.info("MultiStepHandler: delegating to RAG (placeholder)")
        return RagHandler().execute(ctx)
