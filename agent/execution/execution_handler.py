# ============================================================
# BaseExecutionHandler — Abstract interface for all execution handlers
# ============================================================
# Every concrete execution handler (RAG, DirectLLM, Parallel,
# MultiStep, ToolCalling, etc.) must implement this interface.
#
# The handler receives an ExecutionHandlerContext containing
# all runtime dependencies and produces an ExecutionOutput
# with the execution results (context, citations, evidence).
#
# Mirrors:
#   BaseExecutionHandler ↔ BaseExecutionStrategy
#   BaseExecutionHandler ↔ BaseProvider
# ============================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from agent.execution_plan import ExecutionPlan
from agent.execution_engine import ExecutionEngine
from agent.execution_result import ExecutionResult
from agent.reasoning_models import Evidence
from agent.execution.strategy_enums import ExecutionStrategyType


@dataclass
class ExecutionHandlerContext:
    plan: ExecutionPlan

    executor: ExecutionEngine


@dataclass
class ExecutionOutput:
    context: str = ""

    citations: List[Dict[str, Any]] = field(default_factory=list)

    evidences: List[Evidence] = field(default_factory=list)

    execution_results: List[ExecutionResult] = field(default_factory=list)


class BaseExecutionHandler(ABC):

    @property
    @abstractmethod
    def strategy_type(self) -> ExecutionStrategyType:
        ...

    @abstractmethod
    def execute(
        self,
        ctx: ExecutionHandlerContext,
    ) -> ExecutionOutput:
        ...