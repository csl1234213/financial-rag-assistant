# ============================================================
# Execution Context
# ============================================================
# Unified input for the Execution Strategy Layer.
# Aggregates all upstream information — task, complexity,
# and routing — into a single context object that the
# Execution Engine consumes.
# ============================================================

from dataclasses import dataclass

from agent.planning import TaskResult, ComplexityResult
from llm.router import RoutingContext


@dataclass(slots=True)
class ExecutionContext:
    task: TaskResult

    complexity: ComplexityResult

    routing: RoutingContext