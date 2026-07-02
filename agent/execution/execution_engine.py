# ============================================================
# ExecutionEngine — Execution Layer Orchestrator
# ============================================================
# The ExecutionEngine is the single entry point for the
# Execution Strategy Layer. It receives an ExecutionContext,
# selects the best matching strategy via supports(), and
# returns an ExecutionResult.
#
# The Engine does NOT make business decisions.
# It does NOT know about:
#   - Which strategy to use (Strategy decides via supports())
#   - Task types or complexity levels
#   - Provider selection
#   - RAG vs Direct vs Parallel
#
# It ONLY orchestrates:
#   Context → Strategy Selection → Build → Result
#
# Mirrors llm.router.ModelRouter in role:
#   ExecutionEngine ↔ ModelRouter
# ============================================================

from typing import Optional

from .execution_context import ExecutionContext
from .execution_result import ExecutionResult
from .execution_strategy import BaseExecutionStrategy
from .strategy_registry import StrategyRegistry


class ExecutionEngine:

    def __init__(self) -> None:
        self._fallback_strategy_name: Optional[str] = None

    # ============================================================
    # Fallback configuration
    # ============================================================

    def set_fallback(self, strategy_name: str) -> None:
        if not StrategyRegistry.has_strategy(strategy_name):
            raise KeyError(
                f"Fallback strategy '{strategy_name}' not registered. "
                f"Available: {StrategyRegistry.list_strategies()}"
            )
        self._fallback_strategy_name = strategy_name

    # ============================================================
    # Execute
    # ============================================================

    def execute(
        self,
        context: ExecutionContext,
    ) -> ExecutionResult:
        strategies = self._get_sorted_strategies()

        for strategy in strategies:
            if strategy.supports(context):
                return strategy.build(context)

        return self._fallback_execute(context)

    # ============================================================
    # Internal helpers
    # ============================================================

    def _get_sorted_strategies(self) -> list[BaseExecutionStrategy]:
        strategies = StrategyRegistry.list_instances()
        strategies.sort(key=lambda s: s.priority, reverse=True)
        return strategies

    def _fallback_execute(self, context: ExecutionContext) -> ExecutionResult:
        if self._fallback_strategy_name is not None:
            strategy_class = StrategyRegistry.get(self._fallback_strategy_name)
            strategy = strategy_class()
            return strategy.build(context)

        from .strategy_enums import ExecutionStrategyType
        return ExecutionResult(
            strategy=ExecutionStrategyType.DIRECT_LLM,
            reason="No strategy matched; using direct LLM fallback",
            estimated_steps=1,
            parallelism=1,
            use_retrieval=False,
            use_tools=False,
            confidence=0.5,
        )