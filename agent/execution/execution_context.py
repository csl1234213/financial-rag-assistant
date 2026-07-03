# ============================================================
# Execution Context
# ============================================================
# Unified input for the Execution Strategy Layer.
# Aggregates all upstream information — task, complexity,
# routing, and optionally workflow — into a single context
# object that the Execution Engine consumes.
#
# ExecutionEngine 以后永远读取 context.workflow，
# 而不是 workflow_engine。
# ============================================================

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from agent.planning import TaskResult, ComplexityResult
from llm.router import RoutingContext

if TYPE_CHECKING:
    from agent.workflow.workflow_result import WorkflowResult


@dataclass(slots=True)
class ExecutionContext:
    task: TaskResult

    complexity: ComplexityResult

    routing: RoutingContext

    workflow: Optional["WorkflowResult"] = field(default=None)