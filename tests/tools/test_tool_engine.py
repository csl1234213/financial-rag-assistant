import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from agent.tools.base_tool import BaseTool
from agent.tools.implementations import (
    HttpTool,
    PythonTool,
    RetrievalTool,
    SQLTool,
)
from agent.tools.tool_context import ToolContext
from agent.tools.tool_engine import ToolEngine
from agent.tools.tool_enums import ToolStatus, ToolType
from agent.tools.tool_exceptions import ToolNotSupported
from agent.tools.tool_factory import ToolFactory
from agent.tools.tool_registry import ToolRegistry
from agent.tools.tool_result import ToolResult


class TestToolEngine:

    def setup_method(self):
        ToolRegistry.clear()
        ToolFactory._default_tool = None
        ToolRegistry.register("retrieval", RetrievalTool, metadata=RetrievalTool().metadata)
        ToolRegistry.register("python", PythonTool, metadata=PythonTool().metadata)
        ToolRegistry.register("sql", SQLTool, metadata=SQLTool().metadata)
        ToolRegistry.register("http", HttpTool, metadata=HttpTool().metadata)

    def teardown_method(self):
        ToolRegistry.clear()
        ToolFactory._default_tool = None

    # ============================================================
    # Engine creation
    # ============================================================

    def test_tool_engine_creation(self):
        engine = ToolEngine()
        assert isinstance(engine, ToolEngine)

    # ============================================================
    # Factory is called
    # ============================================================

    def test_engine_executes_retrieval_tool_by_string(self):
        engine = ToolEngine()
        result = engine.execute(ToolContext(), "retrieval")
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["tool"] == "RetrievalTool"

    def test_engine_executes_sql_tool_by_enum(self):
        engine = ToolEngine()
        result = engine.execute(ToolContext(), ToolType.SQL)
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["tool"] == "SQLTool"

    def test_engine_executes_python_tool(self):
        engine = ToolEngine()
        result = engine.execute(ToolContext(), "python")
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["tool"] == "PythonTool"

    def test_engine_executes_http_tool(self):
        engine = ToolEngine()
        result = engine.execute(ToolContext(), "http")
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["tool"] == "HttpTool"

    def test_engine_executes_all_tools(self):
        engine = ToolEngine()
        for name, expected_tool in [
            ("retrieval", "RetrievalTool"),
            ("python", "PythonTool"),
            ("sql", "SQLTool"),
            ("http", "HttpTool"),
        ]:
            result = engine.execute(ToolContext(), name)
            assert result.metadata["tool"] == expected_tool

    # ============================================================
    # Registry is called
    # ============================================================

    def test_engine_fails_for_unregistered_tool(self):
        engine = ToolEngine()
        with pytest.raises(Exception):
            engine.execute(ToolContext(), "nonexistent")

    def test_engine_uses_registry_indirectly(self):
        engine = ToolEngine()
        assert ToolRegistry.has_tool("sql") is True
        result = engine.execute(ToolContext(), "sql")
        assert result.status == ToolStatus.SUCCESS

    # ============================================================
    # supports() check
    # ============================================================

    def test_engine_raises_when_supports_false(self):
        class NonSupportingTool(BaseTool):
            @property
            def metadata(self):
                from agent.tools.tool_models import ToolCapability, ToolMetadata
                return ToolMetadata(
                    name="no_support",
                    tool_type=ToolType.CUSTOM,
                    description="Does not support anything",
                    version="0.0.1",
                    capability=ToolCapability(),
                )

            def supports(self, context):
                return False

            def execute(self, context):
                return ToolResult(status=ToolStatus.SUCCESS)

        ToolRegistry.register("no_support", NonSupportingTool)

        engine = ToolEngine()
        with pytest.raises(ToolNotSupported, match="no_support"):
            engine.execute(ToolContext(), "no_support")

    def test_engine_passes_when_supports_true(self):
        engine = ToolEngine()
        result = engine.execute(ToolContext(), "retrieval")
        assert result.status == ToolStatus.SUCCESS

    # ============================================================
    # Hooks
    # ============================================================

    def test_before_execute_hook_called(self):
        class HookedEngine(ToolEngine):
            def __init__(self):
                super().__init__()
                self.before_called = False

            def before_execute(self, context):
                self.before_called = True

        engine = HookedEngine()
        result = engine.execute(ToolContext(), "retrieval")
        assert engine.before_called is True
        assert result.status == ToolStatus.SUCCESS

    def test_after_execute_hook_called(self):
        class HookedEngine(ToolEngine):
            def __init__(self):
                super().__init__()
                self.after_called = False
                self.after_result = None

            def after_execute(self, result):
                self.after_called = True
                self.after_result = result

        engine = HookedEngine()
        result = engine.execute(ToolContext(), "sql")
        assert engine.after_called is True
        assert engine.after_result is result
        assert engine.after_result.status == ToolStatus.SUCCESS

    def test_both_hooks_called_in_order(self):
        call_order = []

        class OrderedEngine(ToolEngine):
            def before_execute(self, context):
                call_order.append("before")

            def after_execute(self, result):
                call_order.append("after")

        engine = OrderedEngine()
        engine.execute(ToolContext(), "http")
        assert call_order == ["before", "after"]

    # ============================================================
    # ToolResult returned
    # ============================================================

    def test_engine_returns_tool_result(self):
        engine = ToolEngine()
        result = engine.execute(ToolContext(), "retrieval")
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata["phase"] == "skeleton"

    def test_engine_with_context_parameters(self):
        engine = ToolEngine()
        ctx = ToolContext(parameters={"query": "SELECT * FROM users", "limit": 10})
        result = engine.execute(ctx, "sql")
        assert isinstance(result, ToolResult)
        assert result.status == ToolStatus.SUCCESS

    # ============================================================
    # Runtime coupling
    # ============================================================

    def test_tool_engine_no_runtime_import(self):
        import agent.tools.tool_engine as m
        source = m.__file__
        with open(source, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue
            if "from agent.agent_runtime" in stripped or "import agent.agent_runtime" in stripped:
                pytest.fail(f"Unexpected Runtime import in tool_engine.py: {stripped}")
