# ============================================================
# Execution Module — Execution Strategy Layer
# ============================================================
# Unified data models for execution strategy selection.
# The Execution Strategy Layer sits between Complexity
# and Routing, determining HOW a task should be executed
# before it reaches the Execution Engine.
#
# Architecture mirrors llm.providers / llm.factory:
#   BaseExecutionStrategy ↔ BaseProvider
#   StrategyRegistry      ↔ ProviderRegistry
#   StrategyFactory       ↔ ProviderFactory
# ============================================================

from .strategy_enums import ExecutionStrategyType
from .execution_context import ExecutionContext
from .execution_result import ExecutionResult
from .execution_strategy import BaseExecutionStrategy
from .strategy_registry import StrategyRegistry
from .strategy_factory import StrategyFactory
from .execution_engine import ExecutionEngine
from .execution_handler import (
    BaseExecutionHandler,
    ExecutionHandlerContext,
    ExecutionOutput,
)
from .execution_handler_registry import ExecutionHandlerRegistry
from .execution_dispatcher import ExecutionDispatcher

__all__ = [
    "ExecutionStrategyType",
    "ExecutionContext",
    "ExecutionResult",
    "BaseExecutionStrategy",
    "StrategyRegistry",
    "StrategyFactory",
    "ExecutionEngine",
    "BaseExecutionHandler",
    "ExecutionHandlerContext",
    "ExecutionOutput",
    "ExecutionHandlerRegistry",
    "ExecutionDispatcher",
]