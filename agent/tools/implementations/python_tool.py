# ============================================================
# PythonTool — Python 代码执行工具
# ============================================================
# 在沙箱中执行 Python 代码片段。
# 当前为骨架实现，execute() 返回固定 ToolResult。
# ============================================================

from agent.tools.base_tool import BaseTool
from agent.tools.tool_context import ToolContext
from agent.tools.tool_enums import ToolStatus, ToolType
from agent.tools.tool_models import ToolCapability, ToolMetadata
from agent.tools.tool_result import ToolResult


class PythonTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="python",
            tool_type=ToolType.PYTHON,
            description="Execute Python code in a sandboxed environment",
            version="1.0.0",
            capability=ToolCapability(
                supports_parallel=False,
                supports_stream=True,
                supports_retry=False,
                supports_async=False,
            ),
        )

    def supports(self, context: ToolContext) -> bool:
        return True

    def execute(self, context: ToolContext) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=None,
            latency_ms=0.0,
            error=None,
            metadata={"tool": "PythonTool", "phase": "skeleton"},
        )
