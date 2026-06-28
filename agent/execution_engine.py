from typing import Any, Callable, Dict, Optional

from agent.execution_plan import ExecutionPlan, PlanStep, StepStatus, StepType
from agent.execution_result import ExecutionResult

Handler = Callable[[PlanStep, Dict[str, Any]], Any]


class ExecutionEngine:
    """
    V3 Execution Engine

    Iterates over ExecutionPlan tasks, dispatches by StepType,
    resolves dependencies, and saves results.

    The engine itself does NOT know about business logic.
    All step handlers are registered externally.
    """

    def __init__(self):
        self._handlers: Dict[StepType, Handler] = {}

    # =========================
    # Handler Registration
    # =========================

    def register_handler(self, step_type: StepType, handler: Handler):
        self._handlers[step_type] = handler

    # =========================
    # Main Entry
    # =========================

    def execute(
        self,
        plan: ExecutionPlan,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        Execute all tasks in the plan.

        Returns the same plan with status and result populated on each step.
        """
        if shared_context is None:
            shared_context = {}

        completed: Dict[int, Any] = {}

        for step in plan.tasks:
            self._execute_step(step, shared_context, completed)

        return plan

    # =========================
    # Step Execution
    # =========================

    def _execute_step(
        self,
        step: PlanStep,
        shared_context: Dict[str, Any],
        completed: Dict[int, Any],
    ):
        if not self._dependencies_met(step, completed):
            step.status = StepStatus.SKIPPED
            step.result = ExecutionResult(
                step_id=step.step_id,
                success=False,
                error="Dependencies not met",
            )
            return

        step.status = StepStatus.RUNNING

        handler = self._handlers.get(step.step_type)

        if handler is None:
            step.status = StepStatus.FAILED
            step.result = ExecutionResult(
                step_id=step.step_id,
                success=False,
                error=f"No handler registered for {step.step_type.value}",
            )
            return

        try:
            output = handler(step, shared_context)
            step.status = StepStatus.COMPLETED
            step.result = ExecutionResult(
                step_id=step.step_id,
                success=True,
                output=output,
            )
            completed[step.step_id] = output
        except Exception as e:
            step.status = StepStatus.FAILED
            step.result = ExecutionResult(
                step_id=step.step_id,
                success=False,
                error=str(e),
            )

    # =========================
    # Dependency Resolution
    # =========================

    def _dependencies_met(
        self,
        step: PlanStep,
        completed: Dict[int, Any],
    ) -> bool:
        if not step.depends_on:
            return True

        for dep_id in step.depends_on:
            if dep_id not in completed:
                return False

        return True
