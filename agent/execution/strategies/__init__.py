# ============================================================
# Strategy Implementations — Skeleton modules
# ============================================================
# All concrete execution strategies live here.
# Each strategy implements the BaseExecutionStrategy interface
# and is automatically registered in StrategyRegistry.
# ============================================================

from .rag_strategy import RagStrategy
from .direct_llm_strategy import DirectLLMStrategy
from .parallel_strategy import ParallelStrategy
from .multi_step_strategy import MultiStepStrategy
from .tool_calling_strategy import ToolCallingStrategy

from ..strategy_registry import StrategyRegistry

# Auto-registration
StrategyRegistry.register("rag", RagStrategy)
StrategyRegistry.register("direct_llm", DirectLLMStrategy)
StrategyRegistry.register("parallel", ParallelStrategy)
StrategyRegistry.register("multi_step", MultiStepStrategy)
StrategyRegistry.register("tool_calling", ToolCallingStrategy)

__all__ = [
    "RagStrategy",
    "DirectLLMStrategy",
    "ParallelStrategy",
    "MultiStepStrategy",
    "ToolCallingStrategy",
]