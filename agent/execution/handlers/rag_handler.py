# ============================================================
# RAGHandler — Execute the RAG pipeline (retrieval + context building)
# ============================================================
# Used when ExecutionResult.strategy == ExecutionStrategyType.RAG
# Executes the plan via the V3 ExecutionEngine, collects evidence,
# and builds context and citations from the retrieved evidence.
# ============================================================

from agent.execution.strategy_enums import ExecutionStrategyType
from agent.execution.execution_handler import (
    BaseExecutionHandler,
    ExecutionHandlerContext,
    ExecutionOutput,
)
from core.context_builder import build_context_from_evidence


class RagHandler(BaseExecutionHandler):

    @property
    def strategy_type(self) -> ExecutionStrategyType:
        return ExecutionStrategyType.RAG

    def execute(
        self,
        ctx: ExecutionHandlerContext,
    ) -> ExecutionOutput:
        shared = {"_all_evidence": []}
        ctx.executor.execute(ctx.plan, shared)
        evidences = shared["_all_evidence"]

        context, citations = build_context_from_evidence(evidences)

        execution_results = [
            step.result for step in ctx.plan.tasks
            if step.result is not None
        ]

        return ExecutionOutput(
            context=context,
            citations=citations,
            evidences=evidences,
            execution_results=execution_results,
        )