# ============================================================
# ToolCallingHandler — Execute with tool calling capability (placeholder)
# ============================================================
# Used when ExecutionResult.strategy == ExecutionStrategyType.TOOL_CALLING
# Placeholder: delegates to RAG handler for now.
# Future: function/tool calling with structured tool execution.
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


class ToolCallingHandler(BaseExecutionHandler):

    @property
    def strategy_type(self) -> ExecutionStrategyType:
        return ExecutionStrategyType.TOOL_CALLING

    def execute(
        self,
        ctx: ExecutionHandlerContext,
    ) -> ExecutionOutput:
        logger.info("ToolCallingHandler: delegating to RAG (placeholder)")
        return RagHandler().execute(ctx)