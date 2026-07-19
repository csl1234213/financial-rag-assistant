# ============================================================
# ToolCallingStrategy — Tool-augmented execution
# ============================================================
# Best for tasks that require external tools such as OCR,
# image analysis, or code execution.
# ============================================================

from ...planning import TaskType
from ..execution_context import ExecutionContext
from ..execution_result import ExecutionResult
from ..execution_strategy import BaseExecutionStrategy
from ..strategy_enums import ExecutionStrategyType


class ToolCallingStrategy(BaseExecutionStrategy):
    @property
    def strategy_name(self) -> str:
        return "tool_calling"

    @property
    def priority(self) -> int:
        return 70

    def supports(self, context: ExecutionContext) -> bool:
        task_type = context.task.task.task_type
        return task_type in (
            TaskType.OCR,
            TaskType.IMAGE_ANALYSIS,
            TaskType.CODE_GENERATION,
        )

    def build(self, context: ExecutionContext) -> ExecutionResult:
        task_type = context.task.task.task_type.value
        return ExecutionResult(
            strategy=ExecutionStrategyType.TOOL_CALLING,
            reason=f"{task_type} task — tool calling required",
            estimated_steps=3,
            parallelism=1,
            use_retrieval=False,
            use_tools=True,
            confidence=0.85,
        )
