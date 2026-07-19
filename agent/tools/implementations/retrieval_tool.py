# ============================================================
# RetrievalTool — 知识检索工具
# ============================================================
# 调用 RAG Pipeline 检索相关文档。
# 当前为骨架实现，execute() 返回固定 ToolResult。
# ============================================================

from agent.tools.base_tool import BaseTool
from agent.tools.tool_context import ToolContext
from agent.tools.tool_enums import ToolStatus, ToolType
from agent.tools.tool_models import ToolCapability, ToolMetadata
from agent.tools.tool_result import ToolResult


class RetrievalTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="retrieval",
            tool_type=ToolType.RETRIEVAL,
            description="Retrieve relevant documents from the knowledge base",
            version="1.0.0",
            capability=ToolCapability(
                supports_parallel=True,
                supports_stream=False,
                supports_retry=True,
                supports_async=True,
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
            metadata={"tool": "RetrievalTool", "phase": "skeleton"},
        )
