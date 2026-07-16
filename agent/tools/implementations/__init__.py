# ============================================================
# Implementations — Auto-registration
# ============================================================
# Importing this package automatically registers all built-in
# tool classes into the ToolRegistry.
#
# Mirrors:
#   agent.tools.implementations.__init__  ↔ agent.memory.memories.__init__
#   agent.tools.implementations.__init__  ↔ agent.workflow.workflows.__init__
# ============================================================

from agent.tools.tool_registry import ToolRegistry

from .http_tool import HttpTool
from .python_tool import PythonTool
from .retrieval_tool import RetrievalTool
from .sql_tool import SQLTool

ToolRegistry.register("retrieval", RetrievalTool, metadata=RetrievalTool().metadata)
ToolRegistry.register("python", PythonTool, metadata=PythonTool().metadata)
ToolRegistry.register("sql", SQLTool, metadata=SQLTool().metadata)
ToolRegistry.register("http", HttpTool, metadata=HttpTool().metadata)

__all__ = [
    "HttpTool",
    "PythonTool",
    "RetrievalTool",
    "SQLTool",
]